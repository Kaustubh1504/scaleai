# set-053 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. How are pre-labels converted to corner coordinates?

`from_xywh` reads `[x, y, w, h]` as floats and builds `Box(x1=x, y1=y, x2=x + w, y2=y + h)`.

### 2. What does evaluate() do per image?

For each image id in sorted order it clips that image's pre-labels and reviewed boxes with `clip_to_image`, maps reviewed boxes by box id (only ids that exist among the pre-labels), classifies every pre-label, counts the rest as added, and then runs `is_out_of_bounds` over the image's reviewed boxes from `rev_by_image`.

### 3. Which rows does load_reviews skip?

It parses the four coordinates with `parse_coord` (blank → None, otherwise float) and skips a row when its coordinate check fails. All kept rows become Box objects with normalised image, box id and label.

### 4. How is IoU computed?

`iou` takes the overlap span on each axis (floored at 0), multiplies them for the intersection, and divides by area(a) + area(b) − intersection. Both overlap and area use `span(lo, hi)`.

### 5. What is in the report's outcomes dict?

It groups the per-pre-label outcomes by the image's dataset (`street`, `warehouse`), with keys like `img-05/B8` and values `accepted`, `adjusted`, `relabeled` or `deleted`.

### 6. What does clip_to_image return?

A list of boxes with x values clamped into [0, width] and y values into [0, height]. It copies the input list first and then sets the coordinates on the boxes in that copy.
