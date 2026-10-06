# Nightly Job Scheduler

The data platform runs a nightly batch of jobs (extracts, joins, model training,
dashboards). This tool replays one night: it loads the job definitions, simulates the
scheduler round by round using the recorded attempt outcomes, and reports what happened
to every job.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: `workers` (jobs that can run in one round) and
  `default_max_retries`.
- `data/jobs.csv`: one row per job definition.
- `data/attempts.csv`: the recorded outcome (`ok` or `fail`) of a job's Nth attempt.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Job ids: trim and upper-case (` j02` → `J02`), everywhere they appear, including
  inside `depends_on` and in `attempts.csv`.
- `depends_on` is a `;`-separated list of job ids. Blank means the job has no
  dependencies. Stray spaces around ids are ignored.
- `enabled`: `true`, `yes`, `y` and `1` (any case) mean enabled; any other non-blank value
  means disabled. Blank means enabled. Disabled jobs are left out of the run entirely
  (they never run and do not appear in the report).
- `max_retries`: blank means `default_max_retries` from the config.
- `submitted_at` uses `2026-06-01 08:00`, `2026-06-01T08:00:00` or `01/06/2026 08:00`
  (**day/month/year**).
- `outcome`: trim, any case. A missing `(job, attempt)` row means that attempt succeeded.

### Scheduling

1. A job is **ready** when its status is `pending` and every job in `depends_on` has
   status `succeeded`.
2. The scheduler works in rounds, numbered from 1. Each round it takes the ready jobs in
   priority order and runs the first `workers` of them. **A higher `priority` number is
   more urgent.** Ties: earlier `submitted_at` first, then lower job id.
3. Running a job is one attempt. If the outcome is `ok`, the job is `succeeded`.
4. If it fails, the job may be retried: a job gets at most `max_retries + 1` attempts in
   total. A job with retries left stays `pending` and competes again from the next round.
   A job that has used all its attempts becomes `dead`.
5. When a job becomes `dead`, every pending job that depends on it, directly or through
   other jobs, becomes `skipped`.
6. The run ends when a round has no ready jobs.

### Report

`nightshift.reports.build_report()` returns:

- `rounds`: for each round, the job ids that ran in it, in the order they were picked.
- `jobs`: per job id, `status`, `attempts`, and `finished_round` (the round in which it
  became `succeeded` or `dead`; `None` otherwise).
- `summary`:
  - `counts`: number of jobs per status (`succeeded`, `dead`, `skipped`, `pending`);
  - `total_attempts`: attempts across all jobs;
  - `mean_attempts`: `total_attempts` ÷ number of jobs that ran at least once, rounded to
    2 decimals;
  - `busy_minutes`: sum over jobs of `attempts × duration_s`, in minutes, rounded to 1
    decimal.

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
