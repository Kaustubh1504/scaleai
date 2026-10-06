# Preference Leaderboard

Raters compare two model responses to the same prompt and pick the better one (or call
it a tie). This tool cleans the comparisons, keeps one judgement per rater per prompt
and pair, and turns them into per-model win rates, Elo ratings, a leaderboard, and a list
of prompts where raters disagreed.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/raters.json`: the rater registry (`rater_id`, `qualified`).
- `data/comparisons.csv`: `prompt_id`, `model_a`, `model_b`, `winner`, `rater`,
  `created_at`, `swapped`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Prompt ids, model ids and rater ids: trim and lower-case, in both files.
- `qualified` may be a JSON boolean, a number, or a string; as a string `true`, `yes`,
  `y`, `1` (any case) mean qualified. Missing means not qualified.
- `winner` is `a`, `b` or `tie` (any case). Any other value (blank, `skip`, ...) means the
  row is ignored.
- Only rows from **qualified** registry raters count.
- `created_at` is `2026-06-01 09:00`, `06/01/2026 09:00` (month/day/year) or
  `2026-06-01T09:00:00`.

### Position swap

Some raters used an older interface that showed the two responses in reverse order. Their
rows have `swapped` set. When `swapped` is `true`, `yes`, `y` or `1` (any case), `a`
means `model_b` won and `b` means `model_a` won. Any other value, including `false` and
blank, means the row is not swapped. A tie is a tie either way.

### One judgement per rater

The same rater may judge the same prompt and model pair (in either column order) more
than once. Keep only the latest `created_at`; on equal times the later row wins. All
later steps process the kept comparisons in `created_at` order (file order on ties).

### Ratings

- Win rates per model: `games`, `wins`, `ties`, and
  `win_rate = (wins + 0.5 × ties) / games`, rounded to 3 decimals.
- Elo: every model starts at 1000, K = 32. For each comparison, with `a` and `b` the two
  models, `E_a = 1 / (1 + 10^((R_b − R_a) / 400))`, `S_a` is 1 / 0 / 0.5 for a win / loss
  / tie, and `R_a += K(S_a − E_a)`, `R_b −= K(S_a − E_a)`. Final ratings are rounded to 1
  decimal.

### Report

`prefrank.reports.build_report()` returns `used` (number of kept comparisons),
`win_rates`, `elo`, `leaderboard` (model ids, highest Elo first; ties A→Z) and
`contested`: sorted prompt ids where kept comparisons of the **same** pair on that prompt
do not all have the same outcome (a tie counts as its own outcome).

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
