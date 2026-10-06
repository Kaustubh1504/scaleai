# Labeling Challenge Leaderboard

Teams compete in a week-long labeling challenge. Each submission is scored against a
hidden answer set, and organisers can reject a submission (for example, a late or
malformed upload). This tool computes each team's best score and the final leaderboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/teams.json`: registered teams (`team_id`, `name`, `disqualified`).
- `data/submissions.csv`: one row per submission: `correct` answers out of `total`
  questions, and a review `status`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Team ids: trim and upper-case (`t02 ` → `T02`).
- `disqualified` may be a JSON boolean, a number, or a string. As a string, `true`,
  `yes` and `1` (any case) mean disqualified. Missing means not disqualified.
- `status`: trim, any case. Blank means `accepted`. Only `accepted` submissions count;
  everything else (e.g. `rejected`) is ignored for scoring.
- `submitted_at` uses `2026-04-10 09:00`, `04/10/2026 09:00` (month/day/year) or
  `2026-04-10T09:00:00`.

### Scoring

1. A submission's score is `100 × correct ÷ total`, rounded to 1 decimal (a plain
   percentage such as `82.9`).
2. A team's **best** submission is its highest-scoring accepted submission. If two of its
   accepted submissions share the top score, the earlier one is the best.
3. Disqualified teams, unregistered teams, and teams with no accepted submission are not
   ranked.

### Leaderboard

4. Ranked teams are ordered by best score, **highest first**.
5. Teams with the same best score: the team whose best submission came **earlier** ranks
   higher. If that is also equal, the lower team id ranks higher.
6. Positions run 1, 2, 3, … with no shared positions.

### Report

`podium.ranking.build_report()` returns:

- `teams`: for each ranked team, `best_score` and `accepted` (the number of its accepted
  submissions).
- `leaderboard`: `[position, team_id]` pairs in leaderboard order.

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
