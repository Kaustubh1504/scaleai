# Podium Leaderboard

Teams submit models to a three-task benchmark (`gsm8k`, `humaneval`, `mmlu`) and may
resubmit as often as they like until the freeze. This repo builds the public leaderboard
from the submission log: each team's best result per task, an overall score, a
competition ranking and a podium per division.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/teams.csv`: the registry (`team_id`, `name`, `division`, `status`).
- `data/submissions.csv`: one row per submission (`team_id`, `task`, `score`,
  `submitted_at`). Scores are on a 0–100 scale and may be written as `81`, `81.0` or
  `100`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Team ids, divisions and task names: trim and lower-case.
- Teams whose `status` is `withdrawn` (any case) are left out completely. Any other
  status, including blank, is active.
- `submitted_at` is `2026-06-10 09:00`, `06/10/2026 09:00` (month/day/year) or
  `2026-06-10T09:00:00`.

### Which submissions count

1. Submissions from teams that are not active registry teams are ignored.
2. Submissions with a blank score are ignored.
3. The freeze is `2026-06-30 23:59`. A submission made **at** the freeze still counts;
   anything later is ignored.

### Scores

4. A team's result on a task is its **highest** counted score for that task, compared as
   numbers.
5. `score` is the mean of the team's results over all three tasks, where a task with no
   counted submission is `0`, rounded to 2 decimals.
6. `tasks_attempted` is the number of **different** tasks the team has a counted
   submission for.

### Leaderboard

7. Order by `score`, highest first; equal scores are ordered by team id.
8. Competition ranking: teams with equal `score` share a rank, and the next rank skips
   (1, 2, 3, 3, 5, …). Every active team appears, including teams with no submissions.
9. Each division's podium is the first 3 teams of that division in leaderboard order.

### Output

`podium.board.build_board()` returns:

- `leaderboard`: one row per team in leaderboard order, with `team_id`, `name`,
  `division`, `score`, `best` (task → result), `tasks_attempted` and `rank`.
- `podiums`: division → list of team ids.
- `summary`: `teams` (count), `counted_submissions` and `submissions_by_task`
  (task → number of counted submissions).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the leaderboard
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
