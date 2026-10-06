# set-018 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

It loads the thresholds, the robots and the episodes (metadata from episodes.csv, timestamps from frames.json). For each episode it calls `metrics.compute_metrics`, then `validity.check_episode` with that episode's robot, and collects rows of episode, metrics and reasons. The episodes table is built from those rows and `summarize(rows)` builds the summary.

### 2. How does load_episodes match frames.json entries to CSV rows?

It builds a dict keyed by the upper-cased, trimmed `episode_id` from frames.json, then looks each normalised CSV episode id up in it. An id missing from frames.json gets empty timestamp lists, and frames.json entries without a CSV row are never read.

### 3. What does nearest_gap return?

The absolute distance in ms from `t` to the closest value in the sorted list, using bisect to look only at the neighbours on either side, or None if the list is empty.

### 4. What fields does EpisodeMetrics carry, and in what units?

`frames` (count), `span_ms` (last minus first frame, ms), `duration_s` (seconds, from span_ms), `max_gap_ms` (ms) and `sync_rate` (a fraction from 0 to 1).

### 5. What decides whether an episode counts as valid in the summary?

A row is valid when its `reasons` list is empty. `summarize` groups rows by task and computes valid counts and success rates from those rows, and `valid_minutes` sums `span_ms` over valid rows.

### 6. Where does a robot's max_gap_ms come from?

From robots.csv, parsed to int in `load_robots`. `check_episode` compares the episode's `max_gap_ms` against it whenever the robot is known.

### 7. How is success parsed for an episode?

In `load_episodes`: the cell is trimmed, lower-cased and checked for membership in `TRUTHY` (`true`, `yes`, `y`, `1`).
