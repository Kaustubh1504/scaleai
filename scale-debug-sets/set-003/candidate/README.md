# Lease Queue Replay

Workers pull tasks from a shared queue. Pulling a task takes out a **lease**. If the
worker doesn't complete the task before the lease runs out, the task goes back on the
queue, or is dead-lettered once it has used up its attempts. This tool replays a
recorded event log (`data/events.csv`) against the task list (`data/tasks.csv`) and
reports what happened.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Input

- Task ids: trim and upper-case. Worker ids: trim and lower-case. Actions are
  case-insensitive (`lease`, `complete`).
- `priority` is an integer. **A higher number is more urgent** (12 beats 9).
- `max_attempts` blank → 3.
- Timestamps use one of `2026-04-01 08:00:00`, `2026-04-01 08:00`,
  `04/01/2026 08:00` (month/day/year) or `2026-04-01T08:00:00`.

### Replay

Events are processed in file order (the file is already chronological).

1. **Reap first.** Before handling each event, expire every lease that has run its
   course as of that event's timestamp. A lease lasts 15 minutes: it is expired when
   `now − leased_at ≥ 15 minutes`, however many days that is.
2. **Expiry.** When a lease expires, the task is dead-lettered (`dead`) if it has used
   all of its attempts (`attempts ≥ max_attempts`); otherwise it goes back to
   `pending`.
3. **`lease`.** The worker gets the `pending` task with the highest priority. Ties go
   to the earliest `created_at`, then the lowest task id. The task becomes `leased`
   and its `attempts` goes up by 1. If nothing is pending, the worker gets nothing
   (logged as `null`).
4. **`complete`.** It succeeds only if that worker currently holds the lease on that
   task. The task becomes `done`. Any other completion (expired lease, someone
   else's lease, unknown or finished task) is **rejected** and changes nothing.
5. After the last event, reap once more as of `2026-04-02 12:00`.

### Report

`leasequeue.reports.build_report()` returns `dispatch` (every lease event:
`[time, worker, task or null]`), `status` and `attempts` per task, `dead_letter`
(sorted ids), `rejected` (`[time, worker, task]` in event order) and `completed_by`
(worker → successful completions). Times are formatted `YYYY-MM-DD HH:MM`.

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
