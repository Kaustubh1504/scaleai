# set-089 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does load_submissions filter out?

Rows with a blank score, rows whose submission id was already seen (the id is added to `seen` before the window check), and rows outside the window according to `in_window`. Team and benchmark ids are trimmed and lower-cased.

### 2. Where are banned or withdrawn teams removed?

In `build_leaderboard`: after loading, only submissions whose team maps to status `active` in `load_teams` are kept. A blank status defaults to `active`. Non-active team ids go into `excluded_teams`.

### 3. What does team_bests return?

A tuple: a dict team -> {benchmark: best score} using `better()` with the benchmark's direction, and `last_seen`, a dict team -> one datetime built from all of that team's counted submissions on active benchmarks.

### 4. How is the leader of a benchmark picked?

`benchmark_leaders` walks every team that has a best on that benchmark and keeps the entry that is `better()` than the current one, so it returns (team, score). Benchmarks nobody entered are left out.

### 5. Which benchmarks does composite divide by?

`total_weight` is the sum of the weights of every active benchmark (6 here), whether or not the team entered it. Missing benchmarks add nothing to `weighted`.

### 6. How does rank_board order rows?

It sorts by `(-composite, last_seen[team], team)` and then writes positions 1..n into `rank`.
