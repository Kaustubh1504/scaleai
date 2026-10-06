# Eval Cup Leaderboard

Teams submit model results to several benchmarks during a fixed contest window. This
tool keeps each team's best result per benchmark, turns those into a weighted composite
score and ranks the teams.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/contest.json`: contest `start` and `end` times.
- `data/teams.json`: registered teams (`id`, `name`, `status`).
- `data/benchmarks.csv`: `benchmark`, `weight`, `direction` (`higher` or `lower` is
  better) and `status` (`active` or `retired`).
- `data/submissions.csv`: one row per uploaded result.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Team ids, benchmark names, submission ids, statuses and directions: trim and lower-case.
- A blank team `status` means `active`.
- Times use one of `2026-09-02 10:00`, `09/05/2026 14:30` (month/day/year) or
  `2026-09-06T08:00:00`.
- Rows with a blank `score` are ignored. The export sometimes repeats a row; rows with a
  `submission_id` already seen are the same submission and are ignored.

### Which submissions count

1. Only submissions inside the contest window count: `start <= submitted_at < end`.
   A submission made exactly at `end` is too late.
2. Only submissions from teams whose status is `active` count. Teams with any other
   status are listed in `excluded_teams`.
3. Only `active` benchmarks count.

### Scores

4. A team's **best** on a benchmark is its highest score (`higher`) or lowest score
   (`lower`) among its counting submissions.
5. The benchmark **leader** is the team with the best of all teams' bests.
6. Normalised score: `best / leader_best` for `higher` benchmarks and
   `leader_best / best` for `lower` ones. A benchmark the team did not enter scores 0.
7. `composite` = Σ (weight × normalised score) ÷ Σ weights of **all** active benchmarks,
   rounded to 4 decimals.

### Ranking

8. Teams with at least one counting submission are ranked by composite, highest first.
9. Ties on composite: the team whose **last** counting submission is earlier ranks
   higher (it finished first). Then team id, alphabetically.
10. Ranks are 1, 2, 3, ... with no shared ranks.

### Output

`evalboard.report.build_leaderboard()` returns:

- `board`: ranked rows with `team`, `composite`, `bests` and `rank`;
- `benchmarks`: per active benchmark, `teams` (the number of different teams with a
  counting submission), `leader` and `best` (the leader's score);
- `excluded_teams`: sorted ids of teams that are not active.

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
