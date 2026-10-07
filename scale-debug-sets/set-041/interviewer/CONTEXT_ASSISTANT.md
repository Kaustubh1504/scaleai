# set-041 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads the roster (`load_contributors`) and the graded submissions (`load_submissions`), calls `scoring.leaderboard`, which filters with `eligible`, takes best points per task, counts attempts, sorts and ranks, and then calls `team_standings` on the ranked rows. The summary is built from the counted submissions, the rows and the team table.

### 2. Which submission rows does load_submissions drop?

Rows whose `points` cell is blank after trimming are skipped. Every other row becomes a `Submission` with upper-cased submission and task ids, a lower-cased contributor id, int points and a parsed timestamp. The list is then passed through `first_per_id` before it is returned.

### 3. What does first_per_id return?

A new list in the original order. It walks the submissions, skips one whose `id` is already in its `seen` set, and appends the rest.

### 4. How are attempts counted in leaderboard()?

After `eligible` filters the submissions, every remaining submission adds 1 to its contributor's `attempts`. The same filtered list is returned as the second value and its length becomes `submissions_counted`.

### 5. What is the sort key for leaderboard rows?

`(-score, attempts, contributor_id)`, ascending. The sorted rows then go to `assign_ranks`, which compares `(score, attempts)` with the previous row.

### 6. How is a team's score built?

`team_standings` maps each non-banned roster contributor with a non-blank team to their leaderboard score (0 if absent), then sums the top `TOP_MEMBERS` (2) scores per team. `members` is how many contributors were collected for the team.

### 7. What does the season window look like in code?

`in_season` in scoring.py returns `SEASON_START <= when < SEASON_END`, with the start 2026-04-01 00:00 and the end 2026-04-15 00:00.
