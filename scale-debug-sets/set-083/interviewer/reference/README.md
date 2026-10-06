# Preference Pair Builder

Labelers compare two model responses to the same prompt and rate which one is better.
The responses are shown side by side in random order. This tool screens labelers on a
calibration round, aggregates the remaining ratings into a verdict per pair, exports the
decided pairs as chosen/rejected training examples, and ranks the models.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/labelers.json`: labeler registry (`id`, `name`, `active`).
- `data/pairs.csv`: `pair_id`, `prompt_id`, `model_a`, `model_b`, `gold`. Calibration
  pairs have `gold` set to `A` or `B`; regular pairs leave it blank.
- `data/calibration.csv`: judgements on calibration pairs.
- `data/judgements.csv`: judgements on regular pairs.

Both judgement files have `judgement_id`, `pair_id`, `labeler_id`, `left_model` (the
model whose response was shown on the left), `rating` and `submitted_at`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Pair ids: trim and upper-case. Labeler ids and model names: trim and lower-case
  (`Cobalt-70B` → `cobalt-70b`). `gold`: trim and upper-case.
- `active` may be a JSON boolean, a number or a string (`true`, `yes`, `y`, `1` mean
  active). Only active labelers are screened or counted.
- `submitted_at` is `2026-04-01 09:00`, `04/01/2026 09:00` (month/day/year) or
  `2026-04-01T09:00:00`.
- In **each** judgement file, a labeler who judged the same pair more than once counts
  only once: their latest submission (on equal times, the later row).

### Ratings

- `rating` runs from 1 (the left response is much better) through 4 (equal) to 7 (the
  right response is much better). It is about **screen position**, not about A/B.
- The **margin** of a judgement is expressed in favour of `model_a`: `4 − rating` when
  `model_a` was on the left, `rating − 4` when `model_b` was. Positive favours A.

### Screening (calibration pairs)

- A calibration judgement is correct when its margin is positive and gold is `A`, or
  negative and gold is `B`. A margin of 0 is never correct.
- `accuracy` = correct ÷ calibration pairs judged, rounded to 3 decimals; `None` for a
  labeler with no calibration judgements.
- A labeler is **excluded** when their accuracy is below `0.7`. Labelers with no
  calibration judgements are not excluded.

### Verdicts (regular pairs)

- Only judgements from active, non-excluded labelers count.
- Fewer than 2 counting judgements → `insufficient` (margin `None`).
- Otherwise `margin` = mean of the counting margins, rounded to 2 decimals. If its
  absolute value is below `0.5` the verdict is `tie`; otherwise `A` (positive) or `B`.

### Outputs

`prefpairs.reports.build_report()` returns:

- `labelers`: for each active labeler: `checks`, `accuracy`, `excluded`.
- `pairs`: for each regular pair: `votes`, `margin`, `verdict`.
- `dataset`: one row per pair with verdict `A` or `B`, sorted by pair id:
  `pair_id`, `prompt_id`, `chosen` (the preferred model), `rejected`.
- `standings`: one row per model that appears in a `A`/`B`/`tie` pair, with `wins`,
  `losses`, `ties` and `win_rate` = (wins + 0.5 × ties) ÷ (wins + losses + ties), rounded
  to 3 decimals. Highest win rate first; equal win rates in alphabetical model order.

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
