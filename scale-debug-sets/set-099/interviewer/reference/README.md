# Leasehold

A work queue hands tasks to workers under time-limited **leases**. Workers can extend a
lease with a heartbeat, finish a task with `ack`, or give it back with `nack`. A lease
that runs out puts the task back in the queue, or dead-letters it once it has used all
its attempts. This tool replays one morning's event log and reports what happened.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/tasks.csv`: `task_id`, `type`, `priority`, `created_at`, `max_attempts`.
- `data/workers.json`: `id`, `types` (task types the worker may take), `active` (a JSON
  boolean; missing means active).
- `data/queue.json`: `lease_seconds` per task type.
- `data/events.csv`: `at`, `worker`, `action` (`claim`, `heartbeat`, `ack`, `nack`),
  `task_id` (blank for `claim`). Rows are in time order.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Input

- Task ids: trim, upper-case. Worker ids, task types and actions: trim, lower-case.
- `priority` is an integer and **1 is the most urgent**.
- `max_attempts` blank → 3.
- Times are `2026-05-01 08:00:00`, `2026-05-01 08:00`, `05/01/2026 08:00`
  (month/day/year) or `2026-05-01T08:00:00`.

### Replay

1. **Reap first.** Before each event, expire **every** lease with
   `now ≥ expires_at`. Each expiry is logged, in lease order, with the reap time.
   An expired task goes back to `pending`, or becomes `dead` if
   `attempts ≥ max_attempts`.
2. **Unknown workers.** An event from a worker that is not in the registry, or is
   inactive, is rejected as `unknown_worker`.
3. **`claim`.** The worker gets the most urgent `pending` task among its types: lowest
   priority number, then earliest `created_at`, then lowest id. `attempts` goes up by
   1 and the lease runs for that type's `lease_seconds` from now. If nothing fits, the
   claim is logged with task `null`.
4. **`heartbeat`, `ack`, `nack`** need the worker to hold the task's current lease.
   - `heartbeat`: the lease now ends `lease_seconds` after the heartbeat.
   - `ack`: the task is `done`.
   - `nack`: the task is released right away (pending or dead, as in rule 1).
5. **Rejections** change nothing and are logged with a reason:
   `unknown_task` (no such task), `unknown_worker` (rule 2), `closed` (the task is
   already `done` or `dead`), otherwise `not_holder`.
6. After the last event, reap once more at `2026-05-01 12:00`.

### Report

`leasehold.reports.build_report()` returns `dispatch` (`[time, worker, task]` per
claim), `expired` (`[time, worker, task]`), `rejected`
(`[time, worker, action, task, reason]`), `status` and `attempts` per task,
`dead_letter` (sorted ids) and `mean_ack_seconds`: per task type, the mean number of
seconds from a done task's **first** claim to its ack, rounded to 1 decimal. Times in
the logs are `HH:MM:SS`.

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
