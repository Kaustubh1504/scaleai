# set-042 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

`load_episodes` reads episodes.csv into `Episode` objects, `load_streams` reads streams.json into `{episode_id: {sensor: sorted timestamps}}`, `evaluate_all` turns each episode into `EpisodeStats`, then `task_metrics` and `summarize` build the task table and the summary.

### 2. How does load_streams key the streams?

By `norm_episode(item["episode"])` (trim + upper-case) and then by the sensor name trimmed and lower-cased. Timestamps are converted to int and sorted.

### 3. What does nearest_offset return?

The absolute distance in ms from `t` to the closest value in the sorted `samples` list, looking at the neighbours either side of the bisect insertion point. It returns None for an empty list.

### 4. In what order does evaluate() check the rejection reasons?

missing_stream (no camera or no joints), then too_short (`frames < MIN_FRAMES`, 20), then frame_gap (`max_gap > MAX_GAP_MS`, 150), then unsynced (`sync_ratio < MIN_SYNC_RATIO`, 0.9). If none match, `valid` is set to True.

### 5. What does camera_stats return for a stream?

A tuple `(frames, duration_ms, fps, max_gap)`: the count, last minus first timestamp, the computed frame rate rounded to 2 decimals and the largest consecutive difference. With fewer than 2 frames it returns `(frames, 0, None, None)`.

### 6. Which episodes does task_metrics look at?

Only episodes whose `stats[ep.id].valid` is True, grouped by `ep.task`. Tasks are emitted in sorted order.

### 7. What data does summarize work from?

It builds `valid` from the episodes list, then uses Counters for tags, operators and rejection reasons. The rejection Counter reads from `stats.values()` filtered to invalid ones.
