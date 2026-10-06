# set-090 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. In what order does check_episode run its checks?

Robot lookup, calibration time, required streams (from the raw record), then `prepare()`, the rounded duration range, dropped frames, sync, and finally the outcome label. It returns a Verdict at the first failure. duration_s is filled only for verdicts created after the duration was computed.

### 2. What does prepare() return?

Two lists of integer timestamps: camera and joints. Each stream is read from the record, passed through `to_ms` and `drop_repeats`, and then shifted by an offset from the Robot object.

### 3. How does load_frames handle the unit field?

It stores `norm(item.get("unit") or "ms")` for each episode, so a missing unit becomes `ms` and ` S` becomes `s`. Stream names are lower-cased; the timestamp lists are kept as they are in the file.

### 4. What is the sync rule in code?

`sync_ratio` counts camera timestamps whose `nearest_gap` to the joints list is <= TOLERANCE_MS (25) and divides by the number of camera frames. `in_sync` requires that ratio >= MIN_SYNC_RATIO (0.9). An empty camera or joints list gives 0.0.

### 5. How is the frame-gap limit derived?

`has_dropped_frames` gets the limit from `gap_limit_ms(robot)`, which uses GAP_FACTOR (2.5) and the robot's camera_hz (loaded as a float), and flags the episode if any consecutive camera difference is greater than that limit.

### 6. Where do robot offsets come from when robots.json has null or no value?

load_robots uses `int(item.get(...) or 0)` for both camera_offset_ms and joint_offset_ms, so null or missing becomes 0.

### 7. Which verdicts feed the task table and success rates?

Both `task_table` and `success_rates` iterate over all verdicts and only use those where `v.valid` is True. success_rates counts outcome == "success" as wins.
