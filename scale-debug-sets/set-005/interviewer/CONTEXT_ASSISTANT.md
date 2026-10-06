# set-005 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do?

It loads ground truth (`image_id -> [Box]`) and annotations (`(image_id, annotator) -> [Box]`, after the cutoff filter), runs `evaluate.evaluate` to get one `ImageResult` per image/annotator pair, then builds the `images` dict, the `flagged` list and `annotator_summary`.

### 2. What does geometry.intersection return for two boxes that share exactly one pixel column?

Width = `min(x_max) - max(x_min) + 1` = 1, so the intersection is 1 × the overlapping height, not 0. Non-overlapping boxes give a negative width or height, which is clamped to 0.

### 3. How does greedy_match choose between competing pairs?

It collects `(-iou, pred_index, gt_index)` for every same-label pair with IoU ≥ 0.5 and sorts ascending. That gives the highest IoU first, with ties going to the lower pred index, then the lower gt index. It then accepts pairs whose pred and gt are both still unused.

### 4. How is the review cutoff applied?

`load_annotations` parses `submitted` with `parse_date` and skips the row unless `within_cutoff(date)`, which is `date <= REVIEW_CUTOFF` (2026-05-10).

### 5. How are rows with a blank coordinate handled?

`_box` returns `None` if any of the four coordinate cells is empty after stripping, and both loaders skip `None` rows. So bob's img_05 car with a blank `y_min` is simply not counted.

### 6. In what order does annotator_summary receive results?

`evaluate` iterates `sorted(preds_by_key.items())`, so results are ordered by the `(image_id, annotator)` key: all of img_01's annotators, then img_02's, and so on.

### 7. What recall does an image with no ground truth get?

`ImageResult.recall` returns 1.0 when TP + FN is 0, so such a pair (e.g. img_06/bob) is never flagged, though its boxes still count as FP.
