# set-066 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads the robot registry (load_robots), the de-duplicated episodes (load_episodes) and the camera/joints streams keyed by (episode_id, sensor) (load_streams). Then it runs validity.check_episode on every episode and passes the results to summarize. camera and joint_samples are built straight from the streams.

### 2. How does check_episode decide the reason?

It looks up the robot and both streams, computes camera_stats, then returns at the first failing check in this order: robot_unavailable, missing_stream, too_short (frame count vs MIN_FRAMES = 6), frame_gap (max_gap_ms vs max_gap_allowed(robot)), desync (sync_ratio vs MIN_SYNC_RATIO = 0.8). The sync ratio is only computed for episodes that reach the last check.

### 3. What does nearest_offset return?

The absolute difference in milliseconds between t and the closest timestamp in the sorted list. It uses bisect_left and compares the samples at positions i-1 and i.

### 4. How are stream units handled?

load_streams trims and lower-cases `unit` (blank becomes 'ms') and calls to_ms on every value, which multiplies 's' values by 1000 and rounds everything to an int. Streams for sensors other than camera and joints are skipped.

### 5. Which episode row wins when an id appears twice in episodes.csv?

load_episodes builds a dict keyed by episode_id from the rows in file order, so a later row overwrites an earlier one, while the dict keeps the position where the id first appeared. EP-02 appears twice; the second row has task 'place'.

### 6. What is in the summary and where does it come from?

reports.summarize gets the list of EpisodeResult objects. It counts valid results by task and by recorded_at date, collects reasons of invalid results into a Counter, averages sync_ratio over valid results and sums their duration_ms.

### 7. What frame rate does each robot have?

robots.json gives rate_hz: 10 Hz for most arms, 20 Hz for arm-03, 15 Hz for arm-06, 25 Hz for arm-10 and 30 Hz for arm-08. arm-04 and arm-08 are inactive, and arm-11 is not in the registry.
