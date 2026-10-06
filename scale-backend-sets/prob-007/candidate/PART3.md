# Part 3: Retries, dead letters and shutdown (about 20 minutes)

Some failures are transient, and some jobs never succeed. Retry the first kind
with backoff, park the second kind in a dead-letter queue (DLQ) where an
operator can inspect and replay them, and stop the pool cleanly.

## Contract (keep these signatures)

```python
pool.dead_letters               # -> list[dict], oldest first
pool.drain(max_ticks=100)       # -> list[str]
```

## Retries with backoff

This replaces the Part 1 rule for `TaskFailedError`.

* A job's **failures** are its attempts that raised `TaskFailedError`. Worker
  errors (Part 2) are not failures and never count toward `max_attempts`.
* After its `n`-th failure, if `n < max_attempts`, the job stays `"queued"` and
  goes to the **back** of the queue. It is not eligible before
  `t + backoff_base_s * 2 ** (n - 1)`, where `t` is `clock.time()` right after
  the failed `process()` call. With the defaults: 1 s after the first failure,
  2 s after the second.
* The plan phase skips jobs that are not eligible yet (`clock.time()` earlier
  than that time). They keep their place in the queue and do not stop the walk.
  A job is eligible again once `clock.time() >=` that time.
* After its `max_attempts`-th failure the job is `"failed"` (as in Part 1) and
  is **dead-lettered** with reason `"max_attempts"`.
* Jobs that go back to the queue through failover are eligible right away
  (no backoff).
* The pool never sleeps and never calls `clock.sleep()`. Waiting happens by the
  caller calling `tick()` again later.

## Poison jobs

A job is **lost** on a worker when its `process()` call raised
`WorkerUnreachableError` or `WorkerTimeoutError`. A job that has been lost on
**2 different workers** is a poison job: instead of failing over again it
becomes `"failed"` and is dead-lettered with reason `"poison"` right away,
whatever its failure count. Being lost twice on the same worker does not count.

## `dead_letters`

A new list with one dict per dead-lettered job, in the order they were
dead-lettered:

```python
{
    "job_id": "broken-001",
    "payload": {...},            # as submitted
    "reason": "max_attempts",    # or "poison"
    "history": [                 # one entry per process() call for this job that raised, in order
        {"worker_id": "w1", "error": "<non-empty string>", "at": 1700000000.0},
    ],
}
```

`at` is `clock.time()` right after the call raised. Changing the returned
list or dicts does not change the pool. A dead-lettered job's `job()` view
has `status: "failed"` and a non-empty `error`.

## Graceful shutdown: `drain(max_ticks=100)`

* From the moment `drain` is called, `submit()` raises `RuntimeError` (for any
  id, new or not).
* It then runs rounds like `run_until_idle(max_ticks)` and returns `pending()`:
  the ids of the jobs that are still queued (waiting for backoff, or with no
  worker to run them), in queue order, so the caller can hand them over.
  `drain` does not wait for backoffs and does not dead-letter anything itself.
* The pool still answers `job()`, `status()`, `results`, `dead_letters`, and
  `tick()` / `on_heartbeat()` keep working after a drain.

## Discussion (no code required)

Be ready to talk about:

* A worker times out *after* finishing a job and we run it again elsewhere.
  What did the outside world see, and how would you make that safe?
* An operator fixes the bug behind 5,000 dead-lettered jobs. What does the
  replay tool look like, and how does it avoid making things worse?
* This coordinator is a single process holding the queue in memory. What
  happens when it crashes, and how would you make it highly available and scale it?
