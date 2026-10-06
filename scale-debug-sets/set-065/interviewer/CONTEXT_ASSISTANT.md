# set-065 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_board() do, in order?

It loads active teams, loads counted submissions for them, computes `best_per_task` and `tasks_attempted`, builds one row per active team with `overall(...)` as the score, orders the rows, attaches ranks from `competition_ranks`, then builds podiums per division and the summary from the counted submissions.

### 2. What type is Submission.score?

It is the trimmed string from the CSV; `load_submissions` does not convert it. Conversion to float happens in `best_per_task` when it builds its return value.

### 3. What does best_per_task return?

A dict of team id → {task → float score}, holding the submission that best_per_task kept for each (team, task). Teams with no counted submissions are absent.

### 4. Which rows does load_submissions skip?

Rows whose lower-cased team id is not an active team, rows with a blank score, and rows whose parsed `submitted_at` is compared against the module-level `FREEZE` (2026-06-30 23:59) and found to be past it.

### 5. How does overall handle a task the team never submitted?

It sums `best.get(task, 0.0)` over the three names in `TASKS` and divides by 3, then rounds to 2 decimals.

### 6. How are podiums built?

For each division (sorted), it filters the already-ordered leaderboard to that division and takes the first `PODIUM_SIZE` (3) team ids, so ties at the cut-off are decided by leaderboard order.
