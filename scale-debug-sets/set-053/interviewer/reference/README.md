# Pre-label Review QA

A detection model pre-labels images with bounding boxes, and human reviewers then fix
them: they keep, move, relabel or delete each pre-label and can draw new boxes. This
tool compares the reviewed boxes with the model's pre-labels to see how much of the
model's work survived review, and lists reviewed boxes that were drawn past the image
edge.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/images.csv`: `image_id`, `dataset`, `width`, `height` (pixels).
- `data/prelabels.json`: the model's boxes. `bbox` is COCO style `[x, y, width, height]`
  with `(x, y)` the top-left corner.
- `data/reviews.csv`: the reviewed boxes as `x_min, y_min, x_max, y_max`. `box_id` names
  the pre-label the box came from; it is blank for a box the reviewer drew from scratch.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Image ids, dataset names and labels: trim and lower-case. Box ids: trim and
  upper-case (`b2` → `B2`); blank means no box id.
- A review row with any blank coordinate is ignored. `0` is a real coordinate.

### Geometry

- Coordinates are **continuous** and may be fractional. A box from `x_min = 10` to
  `x_max = 30` is 20 wide: width = `x_max − x_min`, height = `y_max − y_min`,
  area = width × height. There is no `+1`.
- IoU = intersection area ÷ (area A + area B − intersection area). Boxes that don't
  overlap have IoU 0.
- A box is **out of bounds** when it extends past the image: `x_min < 0`, `y_min < 0`,
  `x_max > width` or `y_max > height`. A box ending exactly on the edge is inside.
- Before comparing, both pre-labels and reviewed boxes are clipped to the image. The
  out-of-bounds check uses the boxes **as the reviewer drew them**, before clipping.

### Outcomes

For each pre-label, look up the reviewed box with the same image and box id:

1. No such reviewed box → `deleted`.
2. A different label → `relabeled`.
3. Same label and IoU ≥ 0.9 → `accepted`; otherwise `adjusted`.

A reviewed box whose box id is blank or doesn't name a pre-label on that image counts as
**added**.

### Report

`prelabelqa.reports.build_report()` returns:

- `outcomes`: dataset → `{"<image>/<box id>": outcome}` for every pre-label;
- `added`: image → number of added boxes, only for images with at least one;
- `out_of_bounds`: `[image, box id or null, label]` for every out-of-bounds reviewed
  box, by image id and then file order.

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
