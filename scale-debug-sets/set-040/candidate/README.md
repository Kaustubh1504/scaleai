# Batch Job Scheduler

Simulates one day of the batch platform: jobs are released at their scheduled time, wait
for their dependencies, and run on a fixed pool of workers in priority order. Some
attempts fail (scripted in `data/failures.csv`) and are retried. Jobs that can never run
are reported as blocked, and their dependents are skipped.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: `workers`.
- `data/jobs.csv`: `job_id`, `team`, `priority`, `release`, `duration`, `deps`, `deadline`, `max_retries`.
- `data/failures.csv`: `job_id`, `attempt`: that attempt (1-based) of that job fails.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Job ids, team names and dependency ids: trim, lower-case. `deps` is `;`-separated and
  may be blank.
- `release` and `deadline` are clock times (`06:00` or `6:00`); `deadline` may be blank.
- `duration` is `45m`, `1h`, `1h30m` or a bare number of minutes.
- `priority` is an integer; a **higher number is more urgent**. A blank `max_retries` is 0.

### Blocked jobs

- A job that lists a dependency that is not in `jobs.csv` is blocked with reason
  `missing_dep:<id>`, naming the first such dependency in the listed order. **Every**
  listed dependency is checked, not just the first.
- Otherwise, a job on a dependency cycle is blocked with reason `cycle`.
- Blocked jobs never run. Jobs that are still waiting at the end of the day (because a
  dependency was blocked or failed) are `skipped`.

### Scheduling

- Workers are `w1` … `wN`. Time moves from event to event (a release, a finish, a retry
  becoming ready). At each event time, in this order:
  1. Running attempts that end now finish (succeed, or fail if listed in failures.csv).
  2. Every waiting job that is released (or ready to retry) and whose dependencies have
     all succeeded joins the queue.
  3. While there is a free worker and a queued job, the best queued job starts on the
     lowest-numbered free worker. Best = highest priority, then earliest `release`, then
     `job_id`. Several jobs can start at the same instant.
- A failed attempt is retried if the job has retries left (`max_retries` retries, so at
  most `max_retries + 1` attempts). The retry becomes ready 10 minutes after the failure.
  Otherwise the job is `failed`.

### Report

`jobsim.reports.build_report()` returns:

- `jobs`: per job `status`, `attempts`, and `start` / `end` / `worker` of its last attempt;
- `events`: per job that ran, its own log: `start@HH:MM/wN`, `fail@HH:MM`, `done@HH:MM`;
- `blocked`: `{job_id: reason}`;
- `summary`:
  - `teams`: per team, `jobs` (all jobs of the team), `succeeded`, and `busy_min`
    (minutes of every attempt, failed ones included);
  - `late`: sorted ids of succeeded jobs that finished **after** their deadline
    (finishing exactly at the deadline is on time);
  - `utilization`: total busy minutes ÷ (workers × minutes from the first start to the
    last end), 3 decimals.

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
