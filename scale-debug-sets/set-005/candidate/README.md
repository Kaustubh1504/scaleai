# Box Review QA

Annotators draw bounding boxes on images. A reviewer has made ground-truth boxes for the
same images. This tool matches each annotator's boxes to the ground truth, counts hits
and misses, flags image/annotator pairs for re-review, and summarises each annotator.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Input

- `data/ground_truth.csv` and `data/annotations.csv`. Image ids, annotator names and
  labels are trimmed and lower-cased.
- Rows with any blank coordinate are ignored.
- Annotations count only if `submitted` is **on or before** 2026-05-10. Dates are
  `2026-05-08`, `05/08/2026` (month/day/year) or `8 May 2026`.

### Geometry

- Coordinates are **inclusive integer pixel indices**: a box from `x_min=10` to
  `x_max=19` is 10 pixels wide. So width = `x_max − x_min + 1`, and the same for height.
- IoU = intersection area ÷ (area A + area B − intersection area), all in pixels.
  Boxes that don't overlap have intersection 0.

### Matching (per image, per annotator)

1. A candidate pair is an annotator box and a ground-truth box with the **same label**
   and IoU ≥ 0.5.
2. Take candidate pairs from highest IoU down. Ties go to the annotator box that comes
   first in the file, then the ground-truth box that comes first. Each box is matched at
   most once.
3. TP = matched pairs. FP = annotator boxes left unmatched. FN = ground-truth boxes on
   that image left unmatched.
4. recall = TP ÷ (TP + FN). It is 1.0 if the image has no ground truth.
5. A pair is **flagged** for re-review when recall < 0.8.

Only image/annotator pairs with at least one counted annotation are evaluated.

### Report

`boxqa.reports.build_report()` returns:

- `images`: `"<image>/<annotator>"` → `tp`, `fp`, `fn`, `recall` (rounded to 3 decimals);
- `flagged`: flagged keys, sorted;
- `annotators`: per annotator, totals over all their evaluated images: `images` (count),
  `tp`, `fp`, `fn`, `precision` = TP ÷ (TP + FP) and `recall` = TP ÷ (TP + FN), both
  rounded to 3 decimals.

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
