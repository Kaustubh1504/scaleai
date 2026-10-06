# Pairwise Preference Ranking

Raters compared two model responses to the same prompt and picked the better one (or
called a tie). This tool cleans the comparisons, computes each model's win rate, runs
an Elo rating over the comparisons in the order they were collected, and builds a
leaderboard.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/raters.json`: rater `id` and `attention_passed`.
- `data/comparisons.csv`: `comparison_id`, `round` (collection batch, 1, 2, 3, …),
  `prompt_id`, `model_a`, `model_b`, `preference`, `rater`, `skipped`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Model names, rater ids and comparison ids: trim and lower-case.
- `preference` (trim, any case): `a` means `model_a` won, `b` means `model_b` won, `tie`
  is a tie.
- Flags (`skipped`, `attention_passed`) may be JSON booleans, numbers or strings. As
  strings, `true`, `yes`, `y` and `1` (any case) are true; anything else, including a
  blank cell, is false.

### Which comparisons count

A comparison is excluded, with the first reason that applies:

1. `skipped`: the rater skipped it.
2. `rater`: the rater is not in `raters.json` or did not pass the attention check.
3. `invalid`: both sides are the same model, or the preference is not `a`/`b`/`tie`.

### Win rate

4. `games`: number of counting comparisons a model appeared in.
5. `win_rate` = (wins + 0.5 × ties) ÷ games, rounded to 3 decimals.

### Elo

6. Every model starts at 1000. K = 32.
7. Comparisons are applied one at a time in **round order** (round 1 first, numerically);
   within a round, in file order.
8. For each comparison, with ratings `Ra`, `Rb` from before it:
   `Ea = 1 / (1 + 10^((Rb − Ra) / 400))`, `Sa` = 1 for an a-win, 0 for a b-win and 0.5
   for a tie. Then `Ra += K × (Sa − Ea)` and `Rb += K × ((1 − Sa) − (1 − Ea))`.
9. Reported ratings are rounded to 1 decimal.

### Leaderboard

10. Only models with **at least 11** games are eligible. Eligible models are sorted by
    Elo, highest first (ties: name ascending).

`prefrank.reports.build_report()` returns `excluded` (reason → count), `games`,
`win_rates`, `elo` and `leaderboard`.

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
