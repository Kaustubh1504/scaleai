# Teleop Episode QA

Operators record teleoperation episodes on a fleet of robot arms. Each episode logs a
camera stream and a joint-state stream with millisecond timestamps. Before episodes go
into a training set, this tool measures each one, applies the validity rules, and
summarises what is usable per task.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: the validity thresholds.
- `data/robots.csv`: the fleet (`robot_id`, `model`, `max_gap_ms`, `active`).
- `data/episodes.csv`: episode metadata (robot, operator, task, date, `success`).
- `data/frames.json`: per episode, `camera_ms` and `joints_ms` timestamp lists.
  Episodes in this file that are not in `episodes.csv` are ignored.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Episode and robot ids: trim and upper-case (` Ep07` → `EP07`, `rb-02` → `RB-02`).
  Tasks and operators: trim and lower-case.
- `active` (robots) and `success` (episodes): `true`, `yes`, `y`, `1` in any case mean
  true; any other value means false. A blank `active` means the robot is active.
- `recorded_on` uses `2026-07-01`, `07/01/2026` (month/day/year) or `01 Jul 2026`.

### Metrics (per episode)

1. The camera log can repeat a timestamp and is not always in order. A **frame** is one
   distinct camera timestamp; frames are taken in time order.
2. `frames`: number of frames.
3. `duration_s`: (last frame − first frame) in seconds, rounded to 2 decimals.
4. `max_gap_ms`: the largest gap between consecutive frames (0 if fewer than 2 frames).
5. `sync_rate`: the share of frames that have a joint sample within
   `sync_tolerance_ms` (inclusive: exactly 10 ms away still counts), rounded to 3
   decimals.

### Validity

An episode is valid when it breaks none of these rules. `reasons` lists every rule it
breaks, in this order:

- `unknown_robot`: the robot id is not in `robots.csv`; `robot_inactive`: the robot is
  not active;
- `too_short`: `duration_s` below `min_duration_s` (exactly 2.0 s is fine);
- `frame_gap`: `max_gap_ms` **greater than** the robot's `max_gap_ms` (equal is fine);
- `unsynced`: `sync_rate` below `min_sync_rate`.

### Report

`teleop.reports.build_report()` returns:

- `episodes`: per episode id, `frames`, `duration_s`, `max_gap_ms`, `sync_rate`,
  `reasons`.
- `summary`:
  - `by_task`: per task, `episodes` (all), `valid`, and `success_rate` = successful
    valid episodes ÷ valid episodes, rounded to 3 decimals;
  - `valid_minutes`: total time spanned by valid episodes, in **minutes**, rounded to 2
    decimals (computed from the raw millisecond spans, not from the rounded
    `duration_s`).

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
