# Pre-label QA

Two detection models pre-label images before human annotators see them. A reviewer has
drawn ground-truth boxes for a QA sample. This tool matches each model's predictions to
the ground truth, scores both models, and lists the images where a model's pre-labels
could be accepted without human edits.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/images.csv`: `image_id`, `width`, `height` (pixels). Only these images are
  evaluated.
- `data/ground_truth.csv`: one reviewer box per row, `x1, y1, x2, y2` in **pixels**.
- `data/predictions.json`: one prediction per entry: `model`, `image`, `label`, `score`,
  and `box` = `[cx, cy, w, h]` **normalised** to the image size (centre point, width and
  height as fractions of the image width/height).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Image ids, model names and labels: trim and lower-case.
- Rows for images not in `images.csv` are ignored.
- `score` is a number or a numeric string. A prediction is dropped when its score is
  missing or blank, or below `0.30` (exactly `0.30` is kept).

### Geometry

- All coordinates are **continuous pixel edges**: a box from `x1 = 100` to `x2 = 200` is
  exactly 100 pixels wide. Width = `x2 − x1`, height = `y2 − y1`, area = width × height.
  There is no `+ 1` anywhere.
- A normalised prediction converts to pixels as `x1 = (cx − w/2) × width`,
  `x2 = (cx + w/2) × width`, and likewise for y with the image height.
- IoU = intersection area ÷ (area A + area B − intersection area). Boxes that only touch
  or don't overlap have IoU 0.

### Matching (per model, per image)

1. Predictions are taken in descending score order (equal scores keep file order).
2. Each prediction may match a ground-truth box of the **same label** that is still
   unmatched **for this model** and has IoU **≥ 0.5**. Among those it takes the highest
   IoU; equal IoU goes to the ground-truth box that comes first in the file.
3. TP = matched predictions, FP = unmatched predictions, FN = ground-truth boxes on the
   image left unmatched.
4. Each model is scored independently against the full ground truth: one model's matches
   never affect another model.

### Report

`prelabel.reports.build_report()` returns:

- `images`: `"<model>/<image>"` → `tp`, `fp`, `fn`, for every model and every image;
- `models`: per model, totals `tp`, `fp`, `fn`, `precision` = TP ÷ (TP + FP),
  `recall` = TP ÷ (TP + FN) (each rounded to 3 decimals, 0.0 when the denominator is 0),
  `f1` = 2PR ÷ (P + R) computed from the rounded P and R, rounded to 3 decimals, and
  `auto_accept`: sorted images that have at least one ground-truth box and where the
  model has FP = 0 and FN = 0;
- `best_model`: the model with the highest `f1` (ties: alphabetically first).

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
