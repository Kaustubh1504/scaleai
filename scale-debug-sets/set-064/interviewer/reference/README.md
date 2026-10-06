# Nightshift Scheduler

Nightshift plans the overnight batch run. Every job belongs to one queue, each queue has
a fixed number of worker slots, and jobs can depend on other jobs in the same queue.
Some attempts fail and are retried after a backoff. This repo simulates the run minute by
minute from a scripted list of attempt outcomes and reports when each job ran.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: `run_start`, `backoff_min`, and `slots` per queue.
- `data/jobs.csv`: one row per job (`job_id`, `queue`, `priority`, `submitted_at`,
  `duration_min`, `max_retries`, `deadline`, `depends_on`).
- `data/attempts.csv`: the scripted outcome (`ok` / `fail`) of each attempt
  (`job_id`, `attempt` starting at 1, `outcome`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Job ids and queue names: trim and lower-case, everywhere they appear (including
  `depends_on`, `attempts.csv` and the `slots` keys).
- `submitted_at` is `2026-05-04 00:20`, `05/04/2026 00:20` (month/day/year) or
  `2026-05-04T00:20:00`. Jobs submitted before `run_start` are already waiting when the
  run begins.
- `deadline` is `HH:MM` on the run day; blank means no deadline.
- `max_retries` blank means `0`. `depends_on` is a `;`-separated list of job ids.
- An attempt with no row in `attempts.csv` succeeds. Outcomes are compared ignoring case
  and spaces.

### Simulation (each queue on its own)

1. Time advances one minute at a time from `run_start`. At each minute, attempts that
   finish at that minute complete first, then free slots are filled.
2. A job is **ready** when it is pending, its ready time has come (its submission time, or
   later after a retry) and every job in `depends_on` is `done`.
3. Ready jobs are dispatched in this order: **priority 1 is the most urgent** (lower
   number first), then earlier `submitted_at`, then job id.
4. An attempt occupies its slot for `duration_min` minutes.
5. When attempt *n* fails, the job is retried if *n* ≤ `max_retries`, so a job gets at
   most `max_retries + 1` attempts. It becomes ready again `backoff_min × n` minutes
   after the failed attempt finished. Otherwise its status is `failed`.
6. A job that never becomes ready (for example because a dependency failed) ends as
   `blocked`.

### Report

`nightshift.report.build_report()` returns:

- `jobs`: job id → `queue`, `status` (`done` / `failed` / `blocked`), `attempts`,
  `first_start` and `finished` (as `HH:MM`, or `None`), and `wait_min`: whole minutes from
  `submitted_at` to the first attempt's start (this can be more than a day for backlog
  jobs).
- `summary`:
  - `attempts_by_queue`: queue → number of attempts run on that queue;
  - `late_jobs`: sorted ids of `done` jobs that finished **after** their deadline.
    Finishing exactly at the deadline is on time.

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
