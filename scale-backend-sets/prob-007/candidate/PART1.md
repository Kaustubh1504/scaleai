# Part 1: Queue and assignment (about 20 minutes)

Build the core of the pool: accept jobs, hand them to workers in rounds, and
record what happened to each one.

Read `pool/coordinator.py` and `mock_services/workers.py` before you start.

## Contract (keep these signatures)

```python
from pool.coordinator import Pool

pool = Pool(workers, clock, concurrency_per_worker=2, job_timeout_s=2.0,
            heartbeat_timeout_s=3.0, max_attempts=3, backoff_base_s=1.0)
pool.submit(job_id, payload=None)  # -> bool
pool.tick()                        # -> int: worker.process() calls made in this round
pool.run_until_idle(max_ticks=100) # already written: tick() until a round sends nothing
pool.job(job_id)                   # -> dict
pool.pending()                     # -> list[str]
pool.status()                      # -> dict
pool.results                       # -> dict[str, Any]
```

The constructor already validates its arguments. `heartbeat_timeout_s`,
`max_attempts` and `backoff_base_s` are used in later parts; ignore them for now.

## Workers

* `workers` is an iterable of worker objects, registered in the order given.
  Two workers with the same `worker_id` raise `ValueError`.
* In this part every registered worker is **up**.
* The pool may only call `worker.process()` / `worker.heartbeat()` and read
  `worker.worker_id`. It must not read a worker's internals (`state`, `alive`,
  `in_flight`, `received`, ...); a real coordinator can't see them.

## `submit(job_id, payload=None)`

* `job_id` must be a non-empty `str`; anything else raises `ValueError`.
* A new id is queued at the **back** of the queue with status `"queued"`, and
  `submit` returns `True`. It does not run anything.
* Job ids are idempotency keys and are never reused. Submitting an id that was
  already submitted (whatever its status now) with an **equal** payload (`==`)
  does nothing and returns `False`. With a different payload it raises
  `ValueError` and changes nothing.
* Later changes the caller makes to the payload object must not affect the job.

## Rounds: `tick()`

Each call is one round with two phases.

**1. Plan.** Walk the queue from front to back. For each job, choose a worker
that is up and has been given fewer than `concurrency_per_worker` jobs in this
round. Among those, pick the **least loaded**:

1. fewest jobs given to it so far in this round; then
2. fewest `process()` calls the pool made to it in earlier rounds; then
3. the earliest registered.

A job for which no worker qualifies stays where it is in the queue, and the
walk goes on to the next job.

**2. Run.** Send the planned jobs one at a time, in the order they were
planned: add 1 to the job's `attempts`, then call
`worker.process(payload, timeout=job_timeout_s)` with the payload as submitted.

* It returns: the job is `"done"`. Store the return value as its result.
* It raises `TaskFailedError`: the job is `"failed"`, and its `error` is a
  non-empty string (for example `str(err)`). The worker stays up. (Part 3
  changes this.)
* Other worker errors are Part 2. Until then they may propagate.

Jobs that are done or failed leave the queue; the rest keep their order.
`tick()` returns how many `process()` calls it made (0 when nothing was
planned).

### Example

Workers `w1`, `w2` (registered in that order), `concurrency_per_worker=2`,
jobs `a b c d e` submitted in that order:

| round | plan | `pending()` after |
|---|---|---|
| 1 | a→w1, b→w2, c→w1, d→w2 | `["e"]` |
| 2 | e→w1 (both have had 2 calls; w1 registered first) | `[]` |
| 3 (after submitting `f`) | f→w2 (w1 has had 3 calls, w2 2) | `[]` |

## Inspection

* `job(job_id)` returns a new dict:
  `{"id", "status", "attempts", "worker_id", "result", "error"}`.
  `status` is `"queued"`, `"done"` or `"failed"`. `attempts` counts every
  `process()` call made for the job. `worker_id` is the worker of its most
  recent attempt (`None` before the first). `result` is the return value for
  a done job, otherwise `None`. `error` is the reason for a failed job,
  otherwise `None`. Unknown id: `KeyError`.
* `pending()` returns the ids of queued jobs, in queue order, as a new list.
* `status()` returns
  `{"queued": int, "done": int, "failed": int, "workers": {worker_id: "up" | "down"}}`
  with job counts by status and every registered worker in registration order.
* `results` is a new dict `{job_id: result}` of the done jobs, in the order
  they completed.

## Constraints

* Use the injected `clock`, never the `time` module. The pool never sleeps.
* The starter tests in `tests/` must keep passing. Write tests for your work
  with `FakeClock` and `MockWorker` (a `handler=` that raises gives you a
  `TaskFailedError`).
