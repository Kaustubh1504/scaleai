# Teleop Episode QA

Operators record teleoperation episodes on a fleet of robot arms. Before an episode goes
into the training set it has to pass a series of quality checks on its sensor streams.
This tool runs those checks and summarises the usable data.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/robots.json`: the fleet: `camera_hz`, per-stream clock offsets
  (`camera_offset_ms`, `joint_offset_ms`; missing or null = 0) and `calibrated_at`.
- `data/tasks.csv`: per task, the allowed duration range (`min_s`, `max_s`) and the
  `;`-separated `required_streams`.
- `data/episodes.csv`: one row per recorded episode.
- `data/frames.jsonl`: one line per episode with the timestamps of each stream. `unit` is
  the unit of those timestamps (`ms` if missing; `s`, `sec` or `seconds` mean seconds).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Episode ids: trim and upper-case. Robot ids, task names, operators, outcomes, stream
  names and units: trim and lower-case.
- Times use one of `2026-10-01 09:00`, `10/01/2026 10:05` (month/day/year),
  `2026-10-01T10:30:00` or a bare date `10/03/2026` (midnight).

### Preparing streams

1. Every stream's timestamps are converted to integer milliseconds using the episode's
   `unit`.
2. Each stream is sorted and repeated timestamps are dropped.
3. Each stream is then shifted onto the robot's common clock by adding that stream's
   offset (`camera_offset_ms` for camera, `joint_offset_ms` for joints).

### Checks (in this order; the first one that fails is the episode's `reason`)

1. `unknown_robot`: the robot is not in `robots.json`.
2. `uncalibrated`: the episode started before the robot's `calibrated_at`.
3. `missing_stream`: a required stream is absent or empty.
4. `too_short` / `too_long`: duration = (last − first camera timestamp) in seconds,
   rounded to 2 decimals, must be within `[min_s, max_s]` (inclusive).
5. `dropped_frames`: some gap between consecutive camera frames is larger than
   2.5 × the camera period (`1000 / camera_hz` ms, not rounded).
6. `out_of_sync`: a camera frame is synced when the nearest joint sample is at most 25 ms
   away. Fewer than 90% of camera frames synced fails.
7. `unlabelled`: the outcome is not `success` or `fail`.

An episode that passes all checks is valid (`reason` is `None`). `duration_s` is
reported whenever check 4 was reached, otherwise `None`.

### Output

`episodeqa.report.build_report()` returns:

- `episodes`: id → `valid`, `reason`, `duration_s`;
- `tasks`: per task with valid episodes, the valid `episodes` (file order) and `total_s`;
- `summary`:
  - `valid_episodes`, and `valid_hours` (total valid seconds ÷ 3600, 4 decimals);
  - `success_rate`: per task, successes ÷ valid episodes, rounded to 3 decimals
    (a task with valid episodes but no successes is `0.0`);
  - `operators`: per operator, `submitted` (all episodes), `valid` and `valid_s`
    (seconds of valid episodes).

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
