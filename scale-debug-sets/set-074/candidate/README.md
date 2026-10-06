# Calibrated Likert Consensus

Annotators rate model responses on a 1–5 quality scale. Two rubric versions are in use
(`v1` and `v2`), and annotators lean differently under each. A few **gold** items have a
known score and are used to measure each annotator's lean (bias) per rubric. This tool
removes that bias from every rating and builds a consensus score for each item.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/annotators.json`: the registry (`id`, `name`, `active`).
- `data/items.csv`: every item with its `rubric`; `gold_score` is filled in for gold items.
- `data/ratings_*.csv`: one row per submitted rating, split into weekly exports. All of
  them are read.
- `data/config.json`: the rating window and the consensus thresholds.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Item ids: trim and upper-case. Annotator ids: trim and lower-case. Rubrics: trim and
  lower-case (`V2 ` → `v2`).
- `active` may be a JSON boolean, a number, or a string (`true`, `yes`, `1` in any case
  mean active).
- `score` must be a whole number from 1 to 5. Rows with anything else (`n/a`, `6`, blank)
  are ignored.
- `submitted_at` is UTC: either epoch **seconds** or `2026-06-08 09:00` /
  `2026-06-08T09:40:00`.

### Which ratings count

1. Ignore ratings for unknown items and from annotators who are not in the registry or
   are inactive.
2. Ignore ratings submitted outside the window. Both `opens` and `closes` are dates and
   both days are included in full.
3. If an annotator rated the same item more than once, only the latest rating counts.

### Calibration

4. An annotator's **bias** for a rubric is the mean of `score − gold_score` over the
   gold items **of that rubric** they rated. With no such ratings, the bias is `0.0`.
5. Each rating on a non-gold item is **adjusted**: `score − bias` (using the bias for
   the item's rubric), then clamped to the range 1–5.

### Consensus (non-gold items)

6. An item with fewer than `min_votes` counting ratings is `insufficient` (score and
   agreement `None`).
7. Otherwise its `score` is the **median** of the adjusted ratings (for an even number of
   ratings, the mean of the two middle values), rounded to 3 decimals.
8. `agreement` is the fraction of adjusted ratings within `tolerance` of the median
   (inclusive), rounded to 3 decimals. The item is `contested` when agreement is below
   `contested_below`, otherwise `agreed`.

### Report

`likert.reports.build_report()` returns:

- `bias`: for each active registry annotator, rubric → bias rounded to 3 decimals, for
  every rubric that appears in `items.csv`.
- `consensus`: for each non-gold item, `status`, `score`, `agreement`, `votes`.
- `summary`: `by_rubric` (rubric → count of items per status: `agreed`, `contested`,
  `insufficient`) and `contested` (sorted item ids).

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
