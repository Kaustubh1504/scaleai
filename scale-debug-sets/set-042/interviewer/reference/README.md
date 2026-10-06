# Teleop Episode QA

Operators record teleoperation episodes on a fleet of robot arms. Each episode has a
camera stream and a joint-state stream (and sometimes a gripper stream), all stamped in
milliseconds from the start of the episode. Before episodes go into a training set they
are checked for missing streams, short recordings, dropped camera frames and
camera/joint sync. This tool runs those checks and builds per-task and fleet summaries.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/episodes.csv`: `episode_id`, `robot`, `operator`, `task`, `recorded_at`,
  `tags` (semicolon-separated, may be blank), `success`.
- `data/streams.json`: a list of `{"episode", "sensor", "t_ms"}` objects, one per stream.
  `t_ms` is a list of integer timestamps in **milliseconds**.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Episode ids: trim and upper-case (`ep-02` → `EP-02`), in both files. Robot, operator,
  task and sensor names: trim and lower-case.
- Tags: lower-case, split on `;`, trim each tag. A blank (or all-whitespace) cell means
  the episode has **no** tags.
- `success`: `true`, `yes`, `y` or `1` (any case) mean success; anything else, including
  blank, means not a success.
- `recorded_at` uses one of `2026-06-01 09:00`, `06/01/2026 09:00` (month/day/year) or
  `2026-06-01T09:00:00`.
- Stream timestamps are sorted ascending before use.

### Per-episode stats

1. `frames` = number of camera timestamps. `duration_s` = (last − first camera
   timestamp) in seconds, rounded to 2 decimals.
2. `fps` = (frames − 1) ÷ duration in seconds, rounded to 2 decimals. (60 frames 40 ms
   apart span 2.36 s, which is 25.0 fps.)
3. `max_gap_ms` = largest difference between consecutive camera timestamps.
4. A camera frame is **synced** if some joint sample lies within 20 ms of it, **inclusive**
   (a joint sample exactly 20 ms away counts). `sync_ratio` = synced frames ÷ frames,
   rounded to 3 decimals; `None` if the episode has no camera or no joint stream.

### Validity

The first rule that matches gives the rejection `reason`; an episode that matches none
is valid (`reason` is `None`).

5. No camera stream or no joint stream → `missing_stream`.
6. Fewer than 20 camera frames → `too_short`.
7. `max_gap_ms` above 150 → `frame_gap` (exactly 150 is fine).
8. `sync_ratio` below 0.9 → `unsynced` (exactly 0.9 is fine).

### Task metrics (valid episodes only)

For each task: `episodes` (count), `success_rate` (successes ÷ episodes, 3 decimals) and
`recorded_s` (total duration in seconds, 2 decimals).

### Summary (valid episodes only, except `rejected`)

- `valid_episodes`: count.
- `tag_counts`: tag → number of valid episodes carrying it.
- `untagged`: sorted ids of valid episodes with no tags.
- `operators`: operator → number of valid episodes.
- `rejected`: reason → number of invalid episodes.

`robolog.report.build_report()` returns `episodes` (id → stats), `tasks` and `summary`.

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
