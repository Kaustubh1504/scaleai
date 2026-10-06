# Lease Broker Replay

Workers pull tasks from a lease-based queue. A worker that polls is handed one task and a
lease on it; it must heartbeat to keep the lease alive and then `ack` (done) or `fail`
(give it back). Operations exports the broker's event log and replays it with this tool
to reconstruct what happened, including a snapshot at a chosen checkpoint.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/tasks.csv`: `task_id`, `priority`, `enqueued_at`, `max_attempts`.
- `data/workers.csv`: `worker_id`, `active`, `pool`.
- `data/events.csv`: `at_ms` (epoch **milliseconds**, UTC), `worker_id`, `action`,
  `task_id` (blank for polls).
- `data/config.json`: `lease_seconds` and the `checkpoint` time (UTC).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Task and worker ids: trim and upper-case (`w2` → `W2`). Actions compare
  case-insensitively.
- `enqueued_at` and `checkpoint` are UTC in one of `2026-07-01 08:58:00`,
  `2026-07-01T08:59:30` or `07/01/2026 08:58:45` (month/day/year).
- A blank `max_attempts` means 3.
- A worker is active for `y`, `yes`, `true` or `1` (any case). Events from workers that
  are not active, or not listed, are ignored completely.
- Events are processed in `at_ms` order; events with the same `at_ms` keep file order.

### Broker rules

1. **Priority 1 is the most urgent.** A task can be handed out once it is `ready` and its
   `enqueued_at` is not after the current time.
2. Before every event, any lease whose expiry time is **at or before** the event time has
   expired. Its task goes back to `ready`, or to `dead` if its attempts have reached
   `max_attempts`.
3. `poll`: a worker holds at most one lease; polling while holding one hands out nothing.
   Otherwise the worker gets the most urgent available task (ties: earliest
   `enqueued_at`, then lowest task id), or nothing if none is available. Handing out a
   task counts one attempt and sets its lease to expire `lease_seconds` later.
4. `heartbeat`: the lease now expires `lease_seconds` after the heartbeat.
5. `ack`: the task is `done`. `fail`: the lease is released and the task goes back to
   `ready`, or to `dead` if its attempts have reached `max_attempts`.
6. A `heartbeat`/`ack`/`fail` that the worker cannot perform is **rejected** and changes
   nothing. Each rejection has exactly one code:
   - `expired`: the worker held this task earlier, but no longer does;
   - `not_owner`: the task exists but this worker never held it;
   - `invalid`: no such task.

### Report

`leasebox.reports.build_report()` returns:

- `final`: task id → `state`, `owner` (worker id while leased, else `None`), `attempts`.
- `polls`: `[worker_id, task_id or None]` for every poll, in processing order.
- `checkpoint`: the same view as `final`, as it stood at the checkpoint time: after every
  event at or before the checkpoint, with leases expiring at or before it already expired.
- `summary`:
  - `completed_by`: worker id → number of tasks it acked;
  - `dead`: sorted ids of dead tasks;
  - `rejected`: counts for `expired`, `not_owner` and `invalid`;
  - `wait`: over the tasks that were handed out at least once, the time from
    `enqueued_at` to the first hand-out, as `mean_s` and `max_s` (seconds, rounded to 1
    decimal).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
