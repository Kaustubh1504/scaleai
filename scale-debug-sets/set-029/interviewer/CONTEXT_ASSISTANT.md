# set-029 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report compute, in order?

It loads ground truth (xyxy) and predictions (xywh converted to xyxy), runs `match_all` to get pred→gt pairs, scores annotators from those pairs with `annotator_scores`, and computes `localization` from `best_iou_per_gt`, which doesn't use the pairs.

### 2. How does match_all group predictions?

It groups predictions by `(image_id, annotator)` and ground truth by `image_id`, runs `match` for each group against that image's ground truth, and merges the resulting dicts.

### 3. What does candidates() return?

A list of `(iou, pred_id, gt_id)` tuples for same-label pairs whose label is in THRESHOLDS and whose IoU is at least that label's threshold.

### 4. How are fn and recall computed?

`fn` is the total number of ground-truth boxes minus that annotator's matched predictions, and recall is tp ÷ total ground-truth boxes, because every annotator is assigned every image.

### 5. Which rows does the loader skip?

Rows where any of the coordinate columns is blank after trimming; `_numbers` returns None for them. In this data that's g11 and p23.

### 6. What shape is a Box?

A frozen dataclass with `x1, y1, x2, y2` floats. `area` multiplies the clamped width and height, and `iou` returns 0.0 when the overlap width or height is not positive.
