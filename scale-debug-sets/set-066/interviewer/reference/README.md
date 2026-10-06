# Teleop Episode QA

Operators record teleoperation episodes on a fleet of robot arms. Each episode has a
camera stream and a joint-state stream, recorded on separate clocks and sometimes in
different units. Before an episode can go into the training set, this tool checks that
the robot was in service, that both streams exist, that the camera did not drop frames,
and that the two streams line up in time. It then summarises the accepted episodes.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/robots.json`: the fleet (`robot_id`, `rate_hz` = camera frame rate, `active`).
- `data/episodes.csv`: one row per uploaded episode (`episode_id`, `robot_id`, `task`,
  `operator`, `recorded_at`).
- `data/streams.json`: sensor streams. Each record has `episode`, `sensor`, `unit` and
  `t` (a list of timestamps).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Episode ids: trim and upper-case (`ep-02` → `EP-02`). Robot ids: trim and lower-case
  (`ARM-03 ` → `arm-03`), both in the registry and in `episodes.csv`. Tasks: trim and
  lower-case.
- `recorded_at` uses one of `2026-04-02 09:10`, `04/02/2026 09:10` (month/day/year) or
  `2026-04-02T09:10:00`.
- `rate_hz` may be a number or a numeric string. A robot with no `active` key is active.
- If an `episode_id` appears more than once, the **later row in the file** replaces the
  earlier one (it is a re-upload). Episodes keep the order in which their id first appears.

### Streams

- Only `camera` and `joints` streams are used (sensor names: trim, any case). Others,
  such as `gripper`, are ignored.
- `unit` is `ms` or `s` (trim, any case); a blank unit means `ms`. Every timestamp is
  converted to **whole milliseconds** (`s` values × 1000, then rounded).
- Within a stream, timestamps are sorted ascending, and a timestamp that appears more
  than once is a re-sent frame: it counts **once**.
- Camera stats per episode: `frames` (number of distinct timestamps), `duration_ms`
  (last − first) and `max_gap_ms` (largest difference between consecutive timestamps).

### Validity

Checks run in this order; the first one that fails is the episode's `reason`:

1. `robot_unavailable`: the robot is not in the registry, or is not active.
2. `missing_stream`: the episode has no camera stream or no joints stream.
3. `too_short`: fewer than **6** camera frames. Exactly 6 is enough.
4. `frame_gap`: some camera gap is **greater than** twice the robot's frame period
   (period = 1000 / `rate_hz` milliseconds). A gap of exactly twice the period is fine.
5. `desync`: the sync ratio is below **0.8**. A camera frame is *synced* when the
   nearest joint sample is **within 20 ms** of it (20 ms itself counts as synced). The
   sync ratio is synced frames ÷ camera frames, rounded to 3 decimals.

An episode that passes all five checks is valid (`reason` is `null`).

### Report

`episodekit.reports.build_report()` returns:

- `episode_ids`: the cleaned, de-duplicated episode ids, in order;
- `camera`: camera stats for every episode that has a camera stream;
- `joint_samples`: number of distinct joint timestamps for every episode with a joints stream;
- `episodes`: for each episode, `valid` and `reason`;
- `summary`:
  - `total` and `valid`: number of episodes, and number of valid episodes;
  - `valid_by_task` and `valid_by_day` (`recorded_at` date, ISO format): counts of
    valid episodes;
  - `invalid_reasons`: reason → number of invalid episodes with that reason;
  - `mean_sync_ratio`: mean sync ratio over valid episodes, rounded to 3 decimals
    (`null` if there are none);
  - `valid_duration_s`: total camera duration of valid episodes in seconds, rounded to 1 decimal.

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
