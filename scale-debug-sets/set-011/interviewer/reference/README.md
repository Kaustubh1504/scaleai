# Preference Leaderboard

Human raters compare two model responses to the same prompt and pick the better one
(or call it a tie). This tool turns those pairwise judgements into per-model win rates,
Elo ratings and a public leaderboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/models.json`: the model registry (`id`, `display_name`).
- `data/comparisons.csv`: one row per judgement: `comparison_id`, `prompt_id`,
  `model_a`, `model_b`, `winner`, `annotator`, `rated_at`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Model ids, annotator names and `winner` values: trim and lower-case
  (` ATLAS-7b ` → `atlas-7b`).
- `winner` is one of `a` (model_a preferred), `b` (model_b preferred), `tie`, `draw`
  (same meaning as `tie`) or `both_bad` (neither response was acceptable). A row with
  any other value, including a blank one, is ignored.
- A row that mentions a model not in the registry is ignored.
- `rated_at` uses one of `2026-04-01 09:10`, `04/01/2026 09:10` (month/day/year) or
  `2026-04-01T09:10:00`.

### Win rates

1. Every remaining row is a **game** for both of its models, including `both_bad` rows.
2. `a`/`b` gives the preferred model a win. `tie`/`draw` gives both models a tie.
   `both_bad` gives neither model a win or a tie.
3. `win_rate` = (wins + 0.5 × ties) ÷ games, rounded to 3 decimals.

### Elo

4. Every model starts at 1000. Games are applied one at a time in `rated_at` order,
   oldest first (equal times keep file order). `both_bad` games are skipped.
5. For model A against model B: expected = 1 / (1 + 10^((R_B − R_A) / 400)),
   score = 1 for a win, 0.5 for a tie/draw, 0 for a loss, and
   R_A' = R_A + 32 × (score − expected). B moves by the same amount in the other
   direction.
6. Ratings are kept at full precision during the updates and rounded to 1 decimal only
   in the report.

### Report

`prefrank.reports.build_report()` returns:

- `models`: for each registered model that played at least one game: `games`, `wins`,
  `ties`, `win_rate`, `elo`.
- `leaderboard`: ids of models with **at least 4** games, highest Elo first (equal Elo:
  alphabetical id). A higher rating is better.
- `annotators`: annotator → number of games they rated, keys sorted.
- `comparisons_used`: number of rows that survived cleaning.

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
