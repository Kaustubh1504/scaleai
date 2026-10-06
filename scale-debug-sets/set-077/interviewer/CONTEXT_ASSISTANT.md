# set-077 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does load_predictions return, and which predictions does it keep?

A nested mapping model -> image_id -> list of (score, Box) in file order. It drops rows whose image is not in images.csv, whose score is missing/blank, or whose score is below MIN_SCORE (0.30), and converts each box to pixels with from_normalized_center.

### 2. What does load_ground_truth return for an image with no reviewer boxes?

An empty list. The result has one key for every image in images.csv (built with gt.get(image, [])); rows for unknown images such as img-12 are ignored.

### 3. How does match_image use the pool argument?

It loops over predictions sorted by descending score, collects (iou, index) candidates from `pool` with the same label that pass the threshold check, asks pick_best for one, and pops that index out of `pool`. It returns (tp, fp); the caller reads fn as len(pool) afterwards.

### 4. In what order are models evaluated in build_report?

sorted(preds), so detr-v2 first, then yolo-s. Both calls to evaluate_model receive the same `gt` dict object from load_ground_truth.

### 5. How is auto_accept computed?

In build_report, after a model's counts are built: sorted images i where gt[i] is non-empty and that model's counts have fp == 0 and fn == 0.

### 6. Which IoUs sit close to the 0.5 threshold in this data?

yolo-s on img-03 (sign, a 128x64 box inside a 128x128 ground truth) and yolo-s on img-04 (car, roughly a 100x51 box inside a 100x100 ground truth). Every other matched pair is well above 0.8.
