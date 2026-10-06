# Lease Heartbeats

Workers take tasks from a shared queue under a time-limited **lease**. A worker keeps a
lease alive by sending heartbeats and finishes the task with an `ack`. Leases that run
out send the task back to the queue, or to the dead-letter list once it has used up its
attempts. This tool replays a recorded event log against the task list and reports what
happened.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/tasks.csv`: `task_id`, `priority`, `enqueued_at`, `max_attempts`.
- `data/events.csv`: `ts`, `worker`, `action` (`lease`, `heartbeat`, `ack`), `task_id`
  (blank for `lease`). The file is in chronological order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Input

- Task ids: trim and upper-case. Worker ids: trim and lower-case. Actions are
  case-insensitive.
- `priority` is an integer. **1 is the most urgent**; larger numbers can wait.
- `max_attempts` blank → 2.
- Times are UTC and come as epoch **milliseconds** (`1775030400000`) or as
  `2026-04-01T08:00:00Z`, `2026-04-01 08:00:00` or `04/01/2026 08:00` (month/day/year).

### Replay

Events are processed in file order.

1. **Reap first.** Before handling each event, expire every lease whose deadline has
   been reached: a lease is expired when `now ≥ deadline`. A heartbeat or ack that
   arrives exactly at the deadline is too late.
2. **Expiry.** An expired task is dead-lettered (`dead`) if `attempts ≥ max_attempts`,
   otherwise it goes back to `pending`.
3. **`lease`.** The worker gets the `pending` task with the most urgent priority. Ties
   go to the earliest `enqueued_at`, then the lowest task id. The task becomes
   `leased`, its `attempts` goes up by 1, and its deadline is `now + 60 s`. If nothing
   is pending, the worker gets nothing (logged as `null`). A worker may hold several
   leases at once.
4. **`heartbeat`.** If the worker holds the live lease on that task, the deadline moves
   to `now + 60 s` (`ok`). Otherwise nothing changes (`rejected`).
5. **`ack`.** If the worker holds the live lease on that task, the task is `done` and
   counts as completed by that worker. Otherwise the ack is rejected and changes
   nothing.
6. After the last event, reap once more as of `2026-04-01T08:10:00Z`.

### Report

`leasebeat.reports.build_report()` returns:

- `dispatch`: every lease event as `[time, worker, task or null]`;
- `heartbeats`: every heartbeat as `[time, worker, task, "ok" | "rejected"]`;
- `rejected_acks`: `[time, worker, task]` in event order;
- `status` and `attempts` per task, and `dead_letter` (sorted task ids);
- `completed_by`: worker → the tasks **that worker** completed, in completion order
  (workers with no completions are left out);
- `mean_wait_s`: mean of (first lease time − `enqueued_at`) over every task that was
  ever leased, **in seconds**, rounded to 1 decimal.

Times in the report are formatted `HH:MM:SS` (UTC).

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
