# Box Audit

Three annotators drew bounding boxes on a small image set. This tool audits their boxes
against the reviewed ground truth: it matches each annotator's boxes to ground-truth
boxes, scores every annotator, and measures how tightly the team as a whole localises
each class.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/ground_truth.csv`: `gt_id`, `image_id`, `label`, and the box corners
  `x1, y1, x2, y2`.
- `data/predictions.csv`: `pred_id`, `image_id`, `annotator`, `label`, and the box as
  exported by the labelling tool: `x, y, w, h` (left, top, width, height).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Ids (`gt_id`, `pred_id`): trim, lower-case. Image ids: trim, upper-case. Annotator
  ids: trim, lower-case (`ANN-3` and `ann-3` are the same person). Labels: trim,
  lower-case.
- A row with any blank coordinate is skipped.

### Geometry

- Coordinates are continuous pixel positions and `x2`/`y2` are **exclusive**: a box
  from `x1 = 10` to `x2 = 50` is 40 px wide. A prediction's corners are
  `(x, y, x + w, y + h)`.
- `IoU = intersection area ÷ union area`. Boxes that only touch (zero-width overlap)
  have IoU 0. IoU can never exceed 1.

### Matching (per image, per annotator)

1. A prediction and a ground-truth box can match only if they have the same label and
   their IoU is at least the label's threshold: `person` 0.5, `car` 0.6, `sign` 0.7.
2. Matching is greedy and one-to-one: take candidate pairs from the **highest IoU
   down**, and accept a pair only if neither box is matched yet.

### Report

`boxaudit.reports.build_report()` returns:

- `matches`: `pred_id → gt_id` for every accepted pair.
- `annotators`: per annotator, `tp` (matched predictions), `fp` (other predictions),
  `fn` (ground-truth boxes they did not match; every annotator is assigned every
  image), `precision`, `recall`, `f1` (= 2·tp ÷ (2·tp + fp + fn)), each rounded to 3
  decimals.
- `localization`: per label, the mean over that label's ground-truth boxes of the best
  IoU any annotator's same-label prediction on that image reaches (0 if none
  overlaps), rounded to 3 decimals. This ignores thresholds and matching.

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
