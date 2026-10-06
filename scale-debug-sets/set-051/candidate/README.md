# Lease Book

Workers pull tasks from named queues (`ingest`, `review`, `export`, ...). Claiming a task
takes out a ten-minute **lease**. A worker that needs more time sends a **heartbeat** to
extend its lease, and finishes with an **ack**. If a lease runs out first, the task goes
back to its queue, or to the dead-letter list once it has used up its attempts. This tool
replays one day's event log (`data/events.csv`) against the task list (`data/tasks.csv`)
and reports what happened.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Input

- Task ids (in both files): trim and upper-case (` t02` → `T02`). Worker names and
  queue names: trim and lower-case. Actions are case-insensitive: `claim`,
  `heartbeat`, `ack`.
- `priority` is an integer. **1 is the most urgent**; larger numbers can wait.
- `max_attempts` blank → 2.
- Times use one of `2026-06-01 09:00`, `06/01/2026 09:00` (month/day/year) or
  `2026-06-01T09:00:00`.
- A `claim` row names a queue and has no task. `heartbeat` and `ack` rows name a task
  and have no queue.

### Leases

Events are processed in file order (the file is already chronological).

1. A lease lasts 10 minutes from when it was taken or last extended. It has
   **expired** once `now ≥ expires_at`; a lease ending at 09:23 is already gone at
   09:23.
2. **Reap first.** Before handling each event, expire every lease that has run out as
   of that event's time. All of them, however many run out at once.
3. When a lease expires, the holder has **lost** it. The task is dead-lettered
   (`dead`) if `attempts ≥ max_attempts`; otherwise it goes back to `pending`.
4. **`claim`.** The worker gets the most urgent `pending` task in the named queue: lowest
   priority number, then earliest `created_at`, then lowest task id. The task becomes
   `leased` and its `attempts` goes up by 1. If the queue has nothing pending, the
   claim gets nothing (`null`). A worker may hold several leases.
5. **`heartbeat`.** Accepted only if that worker currently holds a lease on that task
   and the lease has been extended fewer than 2 times. The lease then ends 10 minutes
   after the heartbeat. Otherwise the heartbeat is **rejected** and changes nothing.
6. **`ack`.** Accepted only if that worker currently holds a lease on that task. The
   task becomes `done`. Otherwise (expired lease, someone else's lease, unknown or
   finished task) the ack is **rejected** and changes nothing.
7. After the last event, reap once more as of `2026-06-01 12:00`.

### Report

`leasebook.reports.build_report()` returns:

- `claims`: every claim event as `[time, worker, queue, task or null]`;
- `status` and `attempts`: per task;
- `rejected`: every rejected heartbeat or ack as `[time, action, worker, task]`, in event
  order;
- `workers`: for every worker with at least one claim event, `claims` (claims that got a
  task), `acks` (accepted acks) and `lost` (leases that expired while they held them);
- `dead_letter`: sorted ids of dead tasks;
- `extensions`: task → number of accepted heartbeats, only for tasks with at least one.

Times are formatted `YYYY-MM-DD HH:MM`.

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
