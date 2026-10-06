# set-017 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() return and how is it built?

It loads teams.json and submissions.csv, calls `scoring.team_stats` to get one `TeamStats` per ranked team, and returns `teams` (best_score and accepted per team id, sorted by id) plus `leaderboard` from `ranking.rank`.

### 2. Which teams does team_stats skip?

Teams whose id is not in the registry, teams with `disqualified` True, and teams whose submissions are all non-accepted. Submissions are grouped by normalised team id first.

### 3. How is a submission marked accepted?

In `load_submissions`, the status cell is trimmed and lower-cased; blank becomes `"accepted"`. `accepted` is True only when that value equals `"accepted"`.

### 4. What is best_at on TeamStats?

The `submitted_at` of the submission returned by `pick_best` for that team, which is a datetime parsed by `loader.parse_time`.

### 5. How does parse_flag treat the disqualified values in teams.json?

Strings are trimmed, lower-cased and checked against {"true", "yes", "1"}; anything else is passed to `bool()`, so `false`/`true` JSON values and numbers keep their truthiness.

### 6. What does rank() return?

A list of `(position, team_id)` tuples, positions starting at 1, in the order produced by its `sorted` call. build_report turns each tuple into a two-element list.
