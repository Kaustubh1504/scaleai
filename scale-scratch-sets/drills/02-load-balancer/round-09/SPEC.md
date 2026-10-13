# 02: In-process load balancer (75 min)

Build it from scratch in Python. There's no starter code. Put everything in `lb/balancer.py`
and your tests in `tests/`. Docs are fine; AI assistants are not. Standard library only.

| Part | Time | What |
|---|---|---|
| 1 | 25 min | Worker/task states and transitions, `submit`, `dispatch`, `complete`, idempotency |
| 2 | 25 min | Heartbeat timeout, task timeout, retries → `DEAD`, stale attempts, deadlines → `EXPIRED` |
| 3 | 15 min | Draining workers, `scaling_decision()` with cooldown |
| — | 10 min | Discussion |

Run your tests from this folder: `python -m pytest tests -q`.

---

## The module

Everything below is importable from `lb.balancer`:

```python
from lb.balancer import LoadBalancer, WorkerState, TaskState, InvalidTransition, ALLOWED_TRANSITIONS
```

```python
LoadBalancer(now, *, heartbeat_timeout=10.0, task_timeout=30.0, max_retries=3, scale_cooldown=30.0)
```

* `now: Callable[[], float]` is an **injected clock**. Every time-dependent rule reads time
  **only** through `now()`; never call `time.time()`, `time.monotonic()` or `sleep`. The tests
  pass a fake clock and move it by hand.
* Single-threaded: no locks needed (see Discussion).
* **Every time comparison is strict `>`**: something is late only when the elapsed time is
  *greater than* the limit. Exactly at the limit is still on time.

### Enums

`enum.Enum` subclasses whose values equal their names (`WorkerState.IDLE.value == "IDLE"`),
declared in this order:

| Enum | Members |
|---|---|
| `WorkerState` | `IDLE`, `BUSY`, `DRAINING`, `FAILED`, `REMOVED` |
| `TaskState` | `PENDING`, `ASSIGNED`, `COMPLETED`, `EXPIRED`, `DEAD` |

`InvalidTransition` is an `Exception` subclass you define.

---

## Part 1: states, submit, dispatch, complete (25 min)

### Worker state machine

`ALLOWED_TRANSITIONS` is a module-level `dict[WorkerState, set[WorkerState]]`. The grader
compares it for equality with exactly this table:

| From | Allowed to |
|---|---|
| `IDLE` | `BUSY`, `DRAINING`, `FAILED` |
| `BUSY` | `IDLE`, `DRAINING`, `FAILED` |
| `DRAINING` | `REMOVED`, `FAILED` |
| `FAILED` | `IDLE`, `REMOVED` |
| `REMOVED` | *(nothing; `set()`)* |

* **Every** worker state change goes through **one** transition method that checks this
  table and raises `InvalidTransition` for a move not in it. No code assigns the state
  field directly anywhere else.
* A move to the **same** state is not in the table, so it is illegal (e.g. draining a
  `DRAINING` worker raises). The **only** exception is the automatic IDLE/BUSY bookkeeping
  below: when the bookkeeping computes the state the worker is already in, it simply does
  nothing (it does not call the transition method).
* **IDLE/BUSY bookkeeping** runs after every change to a worker's in-flight count. If the
  worker is `IDLE` or `BUSY`, its target is `BUSY` when `in_flight ≥ 1` and `IDLE` when
  `in_flight == 0`; if that differs from the current state, transition to it. Workers in any
  other state are left alone (a `DRAINING` worker stays `DRAINING`; Part 3 adds one rule).

### Workers

| Method | Behavior |
|---|---|
| `register_worker(worker_id, capacity=1)` | New worker in `IDLE`, last-seen = `now()`. Callable at any time (workers can join mid-run). Duplicate id in **any** state, including `REMOVED` → `ValueError`. `capacity < 1` → `ValueError`. Returns `None`. |
| `worker_state(worker_id)` | Returns the `WorkerState`. Unknown id → `KeyError`. |

`capacity` is the max number of tasks the worker may hold at once. "Registration order" means
the order `register_worker` was called.

### Tasks

| Method | Behavior |
|---|---|
| `submit(task_id, priority: int, deadline: float \| None = None) -> bool` | New id → task in `PENDING`, return `True`. An id that was **ever** submitted (any state) → return `False` and change **nothing** (not the priority, not the deadline). |
| `task_state(task_id)` | Returns the `TaskState`. Unknown id → `KeyError`. |

Higher `priority` goes first; any int is allowed (negative too). A task's **submission order**
is fixed when it is first submitted and never changes, even when it is requeued.

### `dispatch() -> list[tuple[task_id, worker_id, attempt]]`

Assigns as many pending tasks as possible and returns the assignments **in the order they were
made**. The loop, exactly:

1. Pick the **eligible worker**: state `IDLE` or `BUSY` **and** `in_flight < capacity`. Of
   those, the one with the **fewest in-flight tasks** (an absolute count, not a ratio); ties
   go to the earliest registered. If there is none → **stop**.
2. Take the next `PENDING` task: highest `priority`, ties by **submission order**. If there is
   none → **stop**.
3. If the task has a deadline and `now() > deadline`, mark it `EXPIRED` (never dispatched),
   and go back to step 2 **with the same worker**.
4. Assign: the task becomes `ASSIGNED`, record its **lease** `(worker, attempt,
   assigned_at=now())`, the worker's in-flight count goes up (run the bookkeeping), and append
   `(task_id, worker_id, attempt)`. Go back to step 1.

* `attempt` is `1` the first time a task is assigned; Part 2 increments it.
* `dispatch()` reads `now()` once at the start and uses that value throughout.
* Use a `heapq` keyed `(-priority, submission_seq, task_id)`. Entries whose task is no longer
  `PENDING` are skipped when popped (lazy deletion); you don't search the heap to remove them.
* Nothing pending or no workers → `[]`.

### `complete(worker_id, task_id, attempt) -> bool`

* Returns `True` **only** if the task is `ASSIGNED` and its lease is that exact
  `worker_id` **and** `attempt`. The task becomes `COMPLETED`; the worker's slot is freed
  (bookkeeping runs).
* Anything else (unknown task, unknown worker, wrong worker, wrong/stale attempt, task not
  `ASSIGNED`, already completed) → return `False` and **change nothing**. Never raise.

---

## Part 2: failures, retries, deadlines (25 min)

### Heartbeats

`heartbeat(worker_id) -> None`:

| Worker state | Effect |
|---|---|
| unknown id | `KeyError` |
| `REMOVED` | `InvalidTransition` (nothing changes) |
| `FAILED` | last-seen = `now()`, then `FAILED → IDLE` (recovery) |
| `IDLE`, `BUSY`, `DRAINING` | last-seen = `now()`; state unchanged |

### `fail(worker_id, task_id, attempt) -> bool`

Same lease-matching rule as `complete` (no match → `False`, nothing changes). On a match the
current attempt has **failed**: free the worker's slot, then apply the **failed-attempt rule**,
and return `True` (also when the task ends up `DEAD`).

### The failed-attempt rule (used by `fail`, heartbeat failure and task timeout)

| Condition | Result |
|---|---|
| `attempt > max_retries` | task → `DEAD`, append its id to the dead letter |
| otherwise | task → `PENDING` with `attempt + 1`, back in the queue at its **original** submission position |

So with `max_retries=3` a task gets **4 attempts in total** (1, 2, 3, 4) and dies when attempt 4
fails. With `max_retries=0` it gets exactly one. The old lease is gone: a late `complete` or
`fail` carrying the old attempt number returns `False`.

`dead_letter() -> list[str]`: task ids in the order they became `DEAD` (a copy).

### `tick() -> None`

Reads `now()` once and runs these three steps **in this order**. `tick()` never dispatches.

1. **Heartbeat timeout.** In registration order, every worker in `IDLE`, `BUSY` or `DRAINING`
   with `now − last_seen > heartbeat_timeout` → `FAILED`. Each of its in-flight tasks (in the
   order they were assigned) is a failed attempt (rule above). A `FAILED` worker holds no
   tasks and is never eligible.
2. **Task timeout.** Every task still `ASSIGNED` with `now − assigned_at > task_timeout`, in the
   order they were assigned: free its slot (the worker keeps its state apart from the
   bookkeeping), then it's a failed attempt. Tasks already handled in step 1 are no longer
   `ASSIGNED`, so a task is never counted twice in one tick.
3. **Deadlines.** Every `PENDING` task with a deadline and `now > deadline` → `EXPIRED`. This
   includes a task that was requeued in steps 1–2 of the same tick.

Deadlines apply only to `PENDING` tasks: an `ASSIGNED` task past its deadline keeps running
and can still complete. `EXPIRED`, `DEAD` and `COMPLETED` are final.

---

## Part 3: draining and scaling (15 min)

### `drain_worker(worker_id) -> None`

| Worker state | Effect |
|---|---|
| unknown id | `KeyError` |
| `IDLE` / `BUSY` | → `DRAINING`; then, if `in_flight == 0`, immediately → `REMOVED` |
| `FAILED` | → `REMOVED` directly |
| `DRAINING` / `REMOVED` | `InvalidTransition` (nothing changes) |

* A `DRAINING` worker gets **no new tasks**. Its current tasks run to the end.
* The bookkeeping gains one rule: when a `DRAINING` worker's in-flight count reaches 0
  (its last task completed, failed, or timed out in `tick` step 2), it → `REMOVED`.
* A `DRAINING` worker still heartbeats. If it times out (`tick` step 1) it → `FAILED` like any
  other worker, its tasks are failed attempts, and it forgets it was draining (a heartbeat
  brings it back as `IDLE`; draining it again from `FAILED` removes it).
* `REMOVED` is permanent; the id can never be registered again.

### `scaling_decision() -> int`

Returns `+1` (add a worker), `-1` (remove one) or `0`. It only reads state; it doesn't
expire, dispatch or change anything except the cooldown timestamp.

| Name | Definition |
|---|---|
| `pending` | number of tasks in state `PENDING` |
| `eligible` | workers in `IDLE` or `BUSY` (not `DRAINING`, `FAILED`, `REMOVED`) |
| `cap` | sum of `capacity` over `eligible` |
| `util` | in-flight tasks on `eligible` workers ÷ `cap` |

Checked in this order:

1. **Cooldown.** If an earlier call returned a nonzero value at time `t` and
   `now − t < scale_cooldown` → `0`. (At exactly `t + scale_cooldown` the cooldown is over.)
   Returning `0` never starts a cooldown.
2. `pending > 2 * cap` → `+1`. This includes `cap == 0` with `pending > 0`.
3. `len(eligible) > 1` and `util < 0.25` → `-1`.
4. Otherwise `0`.

Both `+1` and `-1` start the cooldown, and the cooldown blocks both directions.

---

## Walkthrough (the grader replays this exactly)

```python
clock = FakeClock()   # clock() returns clock.t
lb = LoadBalancer(clock, heartbeat_timeout=10, task_timeout=15, max_retries=2, scale_cooldown=20)
```

| # | t | Call | Returns | Why |
|---|---|---|---|---|
| 1 | 0 | `register_worker("w1", capacity=2)`; `register_worker("w2", capacity=1)` | `None`, `None` | both `IDLE`, last-seen 0 |
| 2 | 0 | `submit("a", 1, deadline=5)`, `submit("b", 5)`, `submit("c", 5)`, `submit("d", 3)`, `submit("b", 9)` | `True ×4`, `False` | duplicate `b` changes nothing |
| 3 | 1 | `dispatch()` | `[("b","w1",1), ("c","w2",1), ("d","w1",1)]` | b,c tie at 5 → FIFO; w1/w2 tie at 0 → w1; then w2 (0) beats w1 (1); then only w1 has room; `a` waits. Both `BUSY` |
| 4 | 2 | `complete("w2","c",1)` | `True` | w2 → `IDLE` |
| 5 | 6 | `dispatch()` | `[]` | w2 is free, but `a`: 6 > 5 → `EXPIRED` |
| 6 | 8 | `heartbeat("w1")`; `heartbeat("w2")` | `None`, `None` | last-seen 8 |
| 7 | 16 | `tick()` | `None` | b, d: 16 − 1 = 15, not > 15 → still `ASSIGNED` |
| 8 | 17 | `tick()`; `complete("w1","b",1)` | `None`; `False` | 17 − 1 > 15: b, d → `PENDING` attempt 2, w1 → `IDLE`; the attempt-1 complete is stale |
| 9 | 18 | `heartbeat("w1")`; `dispatch()` | `None`; `[("b","w1",2), ("d","w2",2)]` | b (5) before d (3); w1/w2 tie → w1, then w2 |
| 10 | 19 | `tick()` | `None` | w2: 19 − 8 = 11 > 10 → `FAILED`; d's attempt 2 fails, 2 ≤ 2 → `PENDING` attempt 3 |
| 11 | 20 | `dispatch()` | `[("d","w1",3)]` | w2 is `FAILED`; w1 has 1 of 2 |
| 12 | 21 | `heartbeat("w2")` | `None` | `FAILED → IDLE` |
| 13 | 22 | `drain_worker("w1")`; `submit("e",2)`, `submit("f",2)`, `submit("g",2)`; `scaling_decision()` | `None`; `True ×3`; `1` | w1 → `DRAINING` (2 in flight). eligible = [w2], cap 1, pending 3 > 2 → +1; cooldown starts at 22 |
| 14 | 23 | `complete("w1","b",2)`; `dispatch()` | `True`; `[("e","w2",1)]` | w1 stays `DRAINING` (d left); draining w1 gets nothing |
| 15 | 24 | `fail("w1","d",3)`; `dead_letter()`; `heartbeat("w1")` | `True`; `["d"]`; raises `InvalidTransition` | 3 > 2 → `DEAD`; w1's last task is gone → `REMOVED` |
| 16 | 25 | `scaling_decision()` | `0` | cooldown: 25 − 22 < 20 |
| 17 | 30 | `complete("w2","e",1)`; `register_worker("w3", capacity=3)` | `True`; `None` | |
| 18 | 31 | `dispatch()` | `[("f","w2",1), ("g","w3",1)]` | w2/w3 tie at 0 → w2 (registered first); w2 full → w3 |
| 19 | 32 | `complete("w2","f",1)` | `True` | |
| 20 | 42 | `scaling_decision()` | `0` | cooldown over (42 − 22 = 20); pending 0; util = 1/4 = 0.25, not < 0.25 |
| 21 | 43 | `complete("w3","g",1)`; `scaling_decision()` | `True`; `-1` | 2 eligible, util 0/4 < 0.25 |
| 22 | 44 | `scaling_decision()` | `0` | cooldown from 43 |

---

## Discussion (10 min, out loud)

1. **Concurrency.** Real workers call `heartbeat`/`complete` from other threads, processes or
   machines. Threads vs processes vs asyncio for the balancer itself: what's CPU-bound here and
   what's I/O-bound? How would you guard shared state: one `threading.Lock` around every
   public method, or a single asyncio event loop that owns all state (and why "no `await`
   inside a critical section" matters)? Where does the GIL help or not?
2. **Delivery guarantees.** Is this at-least-once or exactly-once? Why can a task run twice
   (timeout while the worker is slow, not dead)? Why is the attempt number a **fencing token**,
   and what must the *worker's side effects* (DB writes, uploads) do with it to get effectively
   exactly-once (idempotency keys, conditional writes)?
3. **Balancer crash recovery.** If this process dies, what must be persisted to resume
   (tasks with state/attempt/lease, the seq counter, workers, dead letter)? Write-ahead log vs
   snapshot; what happens to leases granted just before the crash; what's safe to rebuild
   (the heap, in-flight counts).
4. **Starvation.** A steady stream of priority-5 tasks starves priority-1 forever. Fix it with
   aging (effective priority grows with wait time). Why does that break a plain heap, and what
   do you do (periodic rebuild, bucketed queues, deadline-based ordering)?
5. **Explain the whole design in 5 minutes**: the state machine, the lease/attempt model,
   the heap with lazy deletion, the order of `tick()`, and the trade-offs you'd change for
   production (multiple balancers, persistence, metrics).

---

## Tests you must write (in `tests/`)

Write these yourself, with a fake clock (a tiny class with `__call__` returning `self.t`):

1. A disallowed move raises `InvalidTransition` (drain twice; heartbeat a `REMOVED` worker).
2. Equal priorities dispatch FIFO; a higher priority jumps ahead.
3. Least-loaded with mixed capacities, ties by registration order.
4. Duplicate `submit` returns `False` and changes nothing.
5. Heartbeat timeout at exactly the limit does **not** fail; just past it does, and its tasks are requeued.
6. Task timeout → requeued with attempt 2; the old attempt's `complete` returns `False`.
7. `max_retries=3` → exactly 4 attempts, then `DEAD` and in `dead_letter()`.
8. A pending task past its deadline is `EXPIRED` and never dispatched.
9. Drain lifecycle: `BUSY → DRAINING → REMOVED` after its last task finishes; no new tasks meanwhile.
10. `scaling_decision` at both thresholds (`pending == 2*cap`, `util == 0.25`) and the cooldown boundary.

## Grading (only after you're done)

```bash
python -m pytest _grader -q -p no:cacheprovider
```

Don't open `_grader/` before you finish; it contains a reference solution.
