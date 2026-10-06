# Part 1: Worker states and failover (about 20 minutes)

Today `LoadBalancer.dispatch()` hands tasks out round robin to every
registered worker, whether or not it is healthy, and the first worker error
crashes the caller. Make routing aware of worker state, and fail over to
another worker when one cannot take the task.

Read `lb/` and `mock_services/workers.py` before you start.

## Contract (keep these signatures)

```python
from lb.balancer import LoadBalancer, NoWorkersAvailable, TaskFailed, DispatchResult
from lb.models import Task, WorkerState

lb = LoadBalancer(clock, task_timeout_s=2.0, heartbeat_timeout_s=3.0,
                  overload_cooldown_s=5.0, max_attempts=3)
lb.add_worker(worker)
lb.remove_worker(worker_id)
lb.worker_state(worker_id)  # -> WorkerState
lb.dispatch(task)           # -> DispatchResult(task_id, worker_id, result, attempts)
```

`heartbeat_timeout_s` and `max_attempts` are used in later parts; ignore them for now.

## Membership

* `add_worker(worker)` works at any time, including between dispatches. A new
  worker starts `ACTIVE`. If a worker with the same `worker_id` is already
  registered, raise `ValueError` and leave the registered worker unchanged.
* `remove_worker(worker_id)` removes the worker; it gets no further tasks.
  Raise `KeyError` if the id is not registered. A removed worker may be added
  again later. It is then treated as newly registered and goes to the end of
  the order.
* `worker_state(worker_id)` returns the worker's current `WorkerState`. Raise
  `KeyError` for an unknown id.

## Routing: `dispatch(task)`

Workers are ordered by registration. A dispatch walks that order **once**,
starting at the first worker registered *after the most recently tried
worker* and wrapping around at the end. "Tried" means `process()` was called,
whatever the outcome. The first dispatch starts at the first-registered
worker. If the most recently tried worker has since been removed, the rule
still applies: start at the first remaining worker registered after it.

Skip workers that are not `ACTIVE` when their turn comes. For each worker you
try:

1. Add 1 to `task.attempts`, then call `worker.process(task.payload, timeout=task_timeout_s)`.
2. If it returns, return `DispatchResult(task.id, worker.worker_id, <return value>, task.attempts)`.
3. If it raises `WorkerOverloadedError`, mark the worker `OVERLOADED` and move on to the next worker.
4. If it raises `WorkerUnreachableError` or `WorkerTimeoutError`, mark the worker `UNREACHABLE` and move on to the next worker.
5. If it raises `TaskFailedError`, the task itself is broken. Raise
   `TaskFailed(task.id, worker.worker_id, reason)` where `reason` is a non-empty
   string (for example `str(err)`). The worker stays `ACTIVE`, and no other
   worker is tried.

If no worker succeeds before the walk ends, or no worker is registered or
`ACTIVE`, raise `NoWorkersAvailable(task.id)`. Other exceptions propagate
unchanged.

`task.attempts` counts every worker the task has been sent to, over all
dispatch calls. `DispatchResult.attempts` is its value after the call.

The worker errors are in `mock_services/workers.py`. The balancer may only
call `worker.process()` and read `worker.worker_id`. It must not inspect a
worker's internals (`state`, `alive`, `in_flight`, ...); a real balancer
can't see them.

### Example

`w1`, `w2`, `w3` registered in that order, `w2` is dead:

| call | workers tried | served by | attempts |
|---|---|---|---|
| 1 | w1 | w1 | 1 |
| 2 | w2 (unreachable), w3 | w3 | 2 |
| 3 | w1 | w1 | 1 |
| 4 | w3 (w2 is skipped) | w3 | 1 |

## Leaving `OVERLOADED` and `UNREACHABLE`

* An `OVERLOADED` worker becomes `ACTIVE` again once
  `clock.time() >= <time it was marked> + overload_cooldown_s`. Nothing runs in
  the background; work it out from the clock when you need it (in
  `worker_state()` and in `dispatch()`).
* An `UNREACHABLE` worker stays `UNREACHABLE` for now. Part 2 adds a way back.

## Constraints

* Use the injected `clock`, never the `time` module.
* The existing tests in `tests/` must keep passing. Write tests for your
  work with `FakeClock` and `MockWorker`. Setting
  `worker.in_flight = worker.capacity` makes a worker reject tasks as
  overloaded; `kill()`, `go_silent()`, `slow()`, `crash_on_next()` and `revive()` do the rest.
