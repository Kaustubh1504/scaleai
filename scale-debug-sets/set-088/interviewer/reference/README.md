# Batch Cluster Day Planner

A small batch cluster runs jobs on worker pools (`cpu`, `gpu`, `io`, `mem`). Given the
job queue, the worker roster and a script of attempt outcomes, this tool simulates one
working day minute by minute and reports what ran where, plus pool usage.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: `day_start` (minute 0 of the simulation), `horizon` (how long to
  simulate) and `retry_backoff`.
- `data/workers.csv`: `worker_id`, `pool`, `status` (`active`, `draining`, `offline`).
- `data/jobs.csv`: `job_id`, `pool`, `priority`, `submitted_at`, `duration`,
  `max_retries`, `depends_on` (`;`-separated job ids), `owner`.
- `data/attempts.csv`: the outcome (`ok` or `fail`) of a given attempt of a job.
  An attempt not listed is `ok`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Job ids (including ids inside `depends_on`): trim and upper-case. Worker ids, pools,
  statuses, outcomes and owners: trim and lower-case. Empty `depends_on` pieces are ignored.
- Times use one of `2026-10-01 08:00`, `10/01/2026 08:00` (month/day/year) or
  `2026-10-01T08:00:00`.
- Durations are `1h`, `40m`, `1200s` or a bare number of minutes. Everything is in
  whole minutes.
- A blank `max_retries` means 2. `0` means the job is never retried.

### Intake

1. A job whose pool has no worker at all in `workers.csv` is rejected as `unknown_pool`.
2. Dependencies on ids that are not accepted jobs are dropped.

### Simulation

3. Only `active` workers take jobs. A pool's **slots** = its number of active workers.
4. Time runs in whole minutes from `day_start` (minute 0) to `horizon` inclusive. A job
   submitted before `day_start` is available from minute 0.
5. At each minute, first finish the attempts that end at that minute, then start new ones.
6. A job can start when it has been submitted, its retry backoff has passed and all of its
   dependencies have **succeeded**. If any dependency failed or is blocked, the job is
   `blocked`.
7. Waiting jobs start in this order: **higher `priority` number first** (5 is the most
   urgent), then earlier `submitted_at`, then job id. Each takes the free active worker of
   its pool with the lowest worker id; a job with no free worker waits.
8. When an attempt fails, the job is retried if it has made at most `max_retries`
   attempts so far, i.e. a job runs at most `1 + max_retries` times. The retry can start
   `retry_backoff × attempts made so far` minutes after the failure. Otherwise the job is
   `failed`.
9. Jobs still waiting or running at the horizon are `pending`.

### Output

`batchsched.report.build_schedule()` returns:

- `intake`: job id → `pool`, `priority`, `duration` (minutes), `depends_on`.
- `rejected`: job id → reason.
- `jobs`: job id → `state`, `attempts`, `worker` (of the last attempt), `start` (first
  attempt) and `end` (when it succeeded or failed), as `HH:MM`, or `None`.
- `report`:
  - `makespan_minutes`: the latest `end`, in minutes from `day_start`;
  - `pools`: per pool, `slots`, `busy_minutes` (total minutes of every attempt that ran
    in the pool) and `utilization` = 100 × busy ÷ (slots × makespan), rounded to 1 decimal;
  - `longest_wait`: the job with the longest wait from `submitted_at` to its first start,
    in whole minutes (ties: lower job id).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the schedule
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
