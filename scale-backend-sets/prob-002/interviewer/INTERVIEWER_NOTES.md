# prob-002 — Lightweight Load Balancer (interviewer notes)

**Mimics:** the reported real round "clone a starter repo and implement a
lightweight load balancer": worker states active/overloaded/unreachable,
dynamic worker joining, heartbeats, failover, and a priority task queue.
**Difficulty:** medium · **Mode:** plain Python (no web framework) · **Starter:** existing repo (`lb/`, ~230 lines) · **Planted bugs:** none

## Setup

```bash
python tools/export_candidate.py prob-002 ~/interview --part1-only   # give the candidate prob-002/
# afterwards, from scale-backend-sets/:
SOLUTION_DIR=~/interview/prob-002 python -m pytest prob-002/interviewer/hidden_tests -q
SOLUTION_DIR=... python -m pytest prob-002/interviewer/hidden_tests -m "not change"   # 80% rule not delivered
```

The hidden tests build `LoadBalancer(FakeClock(start=1000), ...)` and use
`shared.mock_worker.MockWorker` / `WorkerFleet` directly, not the candidate's
`mock_services`. Everything is single-threaded and deterministic. Tests touch
only the public contract in PART1–3 (`lb.balancer`, `lb.models`). If the
candidate moved a class to another module, re-export it in a scratch copy
rather than failing them outright.

## What the candidate should get from reading the repo (first ~5 minutes)

This is a repo starter, and reading it is part of the signal. Strong
candidates run `python -m pytest` and `python -m lb.simulate` first, then
read the code. By minute 5 they should have noticed:

* **`registry.py`**: workers live in a dict, so iteration order is
  registration order. `register()` silently **overwrites** a duplicate id (and
  the dict keeps the *old* position). `unregister()` silently **ignores**
  unknown ids. Part 1 changes both behaviours, to `ValueError` and `KeyError`.
* **`balancer.py`**: `dispatch()` uses an integer `_next % len(workers)`. That
  ignores states, lets every worker exception escape, and **skips a worker
  whenever the list shrinks** (remove `w1` after it was used and the next task
  goes to `w3`, not `w2`). It already passes `timeout=task_timeout_s` and does
  `task.attempts += 1`. The constructor validates its arguments and `failed`
  already exists. `worker_state`, `on_heartbeat`, `check_health`, `submit`,
  `drain` and `pending` are `NotImplementedError` stubs.
* **`models.py`**: `WorkerState` is defined but unused. `Task.attempts` is a
  lifetime counter, which matters in Part 3. `DispatchResult` is frozen.
  `Worker` is a Protocol: only `worker_id`, `process()` and `heartbeat()`.
* **`mock_services/workers.py`**: the four error types and what each means.
  The key line is that `WorkerTimeoutError` means "the task **may or may not
  have run**". Also: a silent worker hangs until the timeout, which moves the
  fake clock forward, and killed or silent workers send no heartbeats.
* **Naming trap:** `shared.mock_worker.WorkerState` (healthy/slow/silent/dead)
  is the worker's *real* state. `lb.models.WorkerState` is the balancer's
  *belief*. A candidate who reads `worker.state` or `worker.alive` from the
  balancer is cheating the abstraction. PART1 forbids it; raise it if you see it.
* **`simulate.py`**: `load_tasks` already skips malformed lines from
  `data/tasks.jsonl` (bad JSON, non-string id, bool/str priority, a
  non-object line). The file also contains a duplicate id (`label-002`),
  which matters for `submit()` in Part 3, and a poison payload that makes the
  demo print `!!` today.

Ask "what did you notice?" at minute 5. It's good evidence for systematic thinking.

## Timeline

### 60-minute mode

| min | what happens |
|---|---|
| 0–5 | Hand over the repo and `PART1.md`. Candidate runs tests and the demo and reads `lb/` (see above). |
| 5–22 | Part 1: registry errors, per-worker state, cooldown, the rotation rule, the failover loop, tests. |
| ~22 | Reveal `PART2.md` once dispatch fails over (edge cases can trail). |
| 22–38 | Part 2: `on_heartbeat` validation, last-seen, `check_health`, recovery, tests with `WorkerFleet`. |
| ~30 | **Drop the mid-part change** (below), once a full heartbeat marks a worker `OVERLOADED`. |
| ~38 | Reveal `PART3.md`. |
| 38–53 | Part 3: heap queue, `drain`, attempt budget, `failed`. |
| 53–60 | Discussion prompts from PART3 / follow-ups below (pick 1–2). |

If the candidate is behind at minute 25, reveal Part 2 anyway. If they are
behind at minute 45, have them sketch `drain()` in words and go to the
discussion.

### 30-minute mode (Part 1 plus the start of Part 2)

| min | what happens |
|---|---|
| 0–3 | Hand over the repo and `PART1.md`; a short read of `balancer.py` and `mock_services/workers.py`. |
| 3–18 | Part 1: states, failover, membership errors, at least one test with a dead worker. |
| 18–19 | Reveal `PART2.md`. Skip the mid-part change. |
| 19–27 | `on_heartbeat` + `check_health` + recovery on heartbeat, with one `WorkerFleet` test. |
| 27–30 | Follow-up #3 (heartbeat false positives). |

Score Part 3 categories as "not observed". Run `test_part1.py` and
`test_part2.py -m "not change"`.

## Mid-part requirement change (Part 2, ~minute 30)

Say, verbatim:

> "Ops says full capacity is too late: by the time a worker reports
> `in_flight == capacity`, the tasks we already sent it are queueing. Treat a
> worker as `OVERLOADED` when a heartbeat reports `in_flight / capacity >= 0.8`.
> Below 0.8 it is `ACTIVE`. Everything else stays the same: the cooldown, the
> dispatch-time `WorkerOverloadedError` handling, and recovery."

What it tests: whether the overload rule is one well-named predicate or is
spread across several `if`s, and whether the candidate thinks about float
comparison. `4 / 5 >= 0.8` happens to be `True`, but strong candidates write
it as integer maths (`in_flight * 5 >= capacity * 4`) or at least ask about
the boundary. They also update their own tests that assumed "full".
Hidden tests: `test_part2.py::test_overloaded_at_80_percent` and
`test_80_percent_heartbeat_diverts_traffic` (marker `change`). Non-change
tests only use loads that both rules agree on: 0, 3/4 (0.75) and full or over.

## Planted bugs

None. The starter's shortcomings (duplicate overwrite, silent unregister,
index-based round robin that skips a worker after a removal, errors
propagating) are existing behaviour that Part 1 asks the candidate to change.
They are listed above so you can tell whether the candidate read the code.

## Hint ladder

Give the lowest hint that unblocks; note each hint in the rubric.

**Part 1**
1. "Where would you keep the balancer's view of each worker? Does the registry need to know about states?" (a per-worker health record keyed by id)
2. "What happens to `_next % len(workers)` when a worker is removed? Can you define 'next' without an index?" (remember the last tried worker, or its registration sequence number)
3. "Write the loop as: build the rotation list once, skip non-ACTIVE workers, `try process()`, and map each exception to a state change or a `raise`."

**Part 2**
1. "Run `WorkerFleet([...]).run(5, sink=print)`. What arrives, and when does a silent worker stop sending?"
2. "What should 'last seen' be for a worker that has never sent a heartbeat?" (its registration time)
3. "Which clock decides staleness: the payload's `ts` or yours? What if the worker's clock is wrong?"

**Part 3**
1. "`heapq` with what tuple gives you priority-desc *and* FIFO within a priority?" (`(-priority, counter, task)`)
2. "If dispatch fails because everything is down, where does the task go? Can you avoid popping it until you know?" (peek, then pop on resolution)
3. "`dispatch()` will try every ACTIVE worker. How do you cap it at the remaining budget without changing `dispatch()`'s contract?" (a private helper with a limit)

## Common pitfalls (what the hidden tests catch)

* Keeping `_next % len(...)`: after `remove_worker("w1")` the next task goes to `w3` (`test_removed_worker_gets_no_more_tasks`).
* Rotation that resumes after the last *successful* worker instead of the last *tried* one (`test_task_failure_raises_and_worker_stays_active`).
* Retrying a `TaskFailedError` on another worker, or marking the worker bad for it.
* Trying the same worker twice in one dispatch, or looping forever when every worker is down.
* Not passing `timeout=`, so a silent worker "hangs" 30 s of fake time (`test_silent_worker_times_out_after_default_timeout`).
* Using `time.time()`: cooldown and staleness never trigger under `FakeClock`.
* Cooldown checked only in `dispatch()`, so `worker_state()` keeps reporting `OVERLOADED` after expiry.
* Staleness from the payload's `ts`; `>=` instead of `>` at the 3-second boundary.
* `check_health()` reviving workers, or heartbeats from unknown/removed workers raising `KeyError`.
* `on_heartbeat` trusting the payload: `capacity=0` raises `ZeroDivisionError` after the 80% change.
* Part 3: `heappop` before dispatch, then losing the task on an unexpected exception or reinserting it behind its peers; continuing the drain past a stuck task (tasks behind it get attempts); ignoring attempts from earlier drains; letting `dispatch()` try more workers than the remaining budget.
* Not something the hidden tests check, but worth raising: a mutable `Task` in the heap with `attempts` changing is fine, but comparing `Task` objects (no counter in the tuple) raises `TypeError` on equal priorities.

## Follow-up questions

**1. "A worker times out *after* finishing the task, and we fail over. Now it has run twice. What do you do?"**
A strong answer covers: timeouts give at-least-once delivery, not
exactly-once, and the LB cannot tell "never ran" from "ran but the reply was
lost". So make tasks idempotent. Send an idempotency key (the task id plus
the attempt) and have workers dedupe on it in a store with a TTL, or make the
side effect a conditional write or upsert. Separate errors that are safe to
retry (`WorkerUnreachableError` before connect, `WorkerOverloadedError`) from
ambiguous ones (timeouts). Optionally hedge only idempotent work. Report
"possibly duplicated" to the caller, and dedupe downstream as well.

**2. "We need three balancer instances in front of one fleet of 500 workers. What changes?"**
Strong: decide what state must be shared. Membership and health can be
eventually consistent: each LB runs its own heartbeat view, or a central
registry (etcd/Consul/Redis with TTL keys) pushes it. Load is best learned
per instance from rejections, or with a power-of-two-choices pick on reported
load instead of global round robin. The queue must not be in process: use a
durable shared queue (SQS, Redis streams, a DB table with
`SELECT ... FOR UPDATE SKIP LOCKED`), with leases so a crashed LB's in-flight
tasks come back. Use consistent hashing when tasks have affinity (caches,
per-tenant ordering) so adding a worker moves only about 1/N of the keys.
Each LB caps its attempts so retries don't multiply across instances.

**3. "A worker pauses for 4 s in GC, or a network partition cuts the LB off from half the fleet. What happens with your heartbeat timeout?"**
Strong: both cases are false positives. The worker is healthy but gets marked
`UNREACHABLE`, so its work fails over and may run twice (see #1). In a
partition, half the fleet "dies" at once and the survivors get a thundering
herd. Mitigations:
* a `SUSPECT` state before `UNREACHABLE`, or requiring k missed heartbeats;
* phi-accrual failure detection (adaptive to observed heartbeat jitter);
* hysteresis on recovery: several good heartbeats before `ACTIVE`, to avoid flapping;
* not trusting worker clocks (we already use our own);
* a "panic threshold": if more than X% of the fleet looks dead at once, assume
  the LB itself is partitioned and keep routing to everyone (Envoy does this);
* active health checks as a second signal;
* tuning the timeout against heartbeat interval and pause times (timeout ≥ 3× interval).

## Reference solution

`reference/lb/`:
* `registry.py`: the starter plus `ValueError` on duplicates and `KeyError` on unknown ids.
* `health.py` (new): the `WorkerHealth` dataclass (state, cooldown deadline,
  last-seen, last load, registration seq), a lazy cooldown expiry in
  `current(now)`, `parse_heartbeat()` validation, and the
  `reports_overload()` predicate (the mid-part change is one line, in integer maths).
* `balancer.py`: `_rotation()` (registration order, starting after the
  registration seq of the last tried worker, so removals need no special
  case) and `_dispatch(task, limit)`, a single loop that maps each worker
  error to a state change. `dispatch()` calls it with no limit; `drain()`
  calls it with `max_attempts - task.attempts`. The queue is a heap of
  `(-priority, seq, task)` plus a set of pending ids. `drain()` peeks and
  pops only once a task is resolved, so nothing is lost on any exception.
* `simulate.py`: the demo now submits and drains with a hanging worker, then revives it.

Lines a candidate must add (verifier: 166 total, excluding tests):
Part 1 ≈ 75 (registry 10, health record + cooldown 15, rotation and failover loop 50),
Part 2 ≈ 50 (validation 15, heartbeat and staleness 15, `on_heartbeat`/`check_health` 20; the change is ~1),
Part 3 ≈ 40 (queue, drain, give-up), plus ~15 optional lines updating the demo.
