# Annotation Sprint Leaderboard

Contributors earn points by completing graded tasks during a two-week sprint. This tool
reads the contributor roster and the raw submission export, builds the individual
leaderboard and the team standings, and prints a short summary.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contributors.csv`: `contributor_id`, `name`, `team` (may be blank), `status`
  (`active`, `inactive` or `banned`, any case).
- `data/submissions.csv`: one row per graded attempt, exported from the grading tool:
  `submission_id`, `contributor_id`, `task_id`, `points`, `submitted_at`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Contributor ids: trim and lower-case (`C-02` → `c-02`). Task ids and submission ids:
  trim and upper-case. Team names: trim, then title-case (`otters ` → `Otters`). Status:
  trim and lower-case.
- `submitted_at` uses one of `2026-04-01 09:00`, `04/01/2026 09:00` (month/day/year) or
  `2026-04-01T09:00:00`.
- A blank `points` cell means the attempt has not been graded yet: ignore the row.
  `0` is a real grade.
- The export sometimes repeats a row. Rows that share a `submission_id` (after cleaning)
  are the same submission: keep only the first one in the file.

### Which submissions count

1. Ignore submissions from contributors who are not in the roster or whose status is
   `banned`. `inactive` contributors still count.
2. The sprint runs from `2026-04-01 00:00` (inclusive) to `2026-04-15 00:00`
   (exclusive). Ignore submissions outside that window.

### Leaderboard

3. A contributor's **score** is the sum, over the tasks they attempted, of their best
   points on that task.
4. `tasks_solved` = number of tasks whose best points are above 0. `attempts` = number of
   counted submissions.
5. Only contributors with at least one counted submission appear.
6. Order: higher score first. Equal scores: **fewer** attempts first. Still equal: lower
   contributor id first.
7. Ranks use standard competition ranking over `(score, attempts)`: rows with the same
   score and attempts share a rank, and the next rank skips accordingly (1, 2, 2, 4).

### Teams

8. A team's members are its roster contributors who are not banned (contributors with a
   blank team belong to no team). A member with no counted submissions scores 0.
9. Team **score** = sum of its **two** highest member scores. `members` = number of
   members.
10. Order: higher team score first; equal scores in alphabetical team-name order.

### Report

`ladder.teams.build_report()` returns `leaderboard` (list of rows with `rank`,
`contributor_id`, `name`, `score`, `tasks_solved`, `attempts`), `teams` (list of `team`,
`score`, `members`) and `summary`:

- `submissions_counted`: number of submissions that count (after all the rules above);
- `contributors_ranked`: number of leaderboard rows;
- `leader`: contributor id of the first leaderboard row;
- `top_team`: name of the first team.

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
