# set-077 answer key: Detection pre-label QA: two models vs ground truth

**Domain:** bbox_qa  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_image_matching.TestImageMatching.test_yolo_images`
- `tests.test_2_model_summary.TestModelSummary.test_auto_accept`
- `tests.test_2_model_summary.TestModelSummary.test_best_model`
- `tests.test_2_model_summary.TestModelSummary.test_yolo_totals`

## Bugs (recommended order)

### B1: Area computed with inclusive +1

- **Type:** iou-inclusive-exclusive
- **Symptom:** Test 1 test_yolo_images: yolo-s img-03 and img-04 become {tp 0, fp 1, fn 1}. Test 2: yolo totals are (8, 2, 4, 0.8, 0.667, 0.727) instead of (10, 0, 2, 1.0, 0.833, 0.909), img-03/img-04 drop out of yolo's auto_accept, and best_model flips to 'detr-v2'. detr-v2 is unaffected.
- **Location:** `prelabel/geometry.py` → `area`
- **Why it fails:** The +1 belongs to inclusive integer pixel indices, but these boxes use continuous edges. Each area is inflated while the intersection is not, so every IoU shrinks and borderline matches (yolo-s img-03 at exactly 0.5, img-04 at 0.51) fall below the threshold.
- **Unblocks:** yolo-s rows in Test 1 and yolo totals/auto_accept in Test 2; it also exposes B3.

Fix:

```diff
-    return (box.x2 - box.x1 + 1) * (box.y2 - box.y1 + 1)
+    return max(0.0, box.x2 - box.x1) * max(0.0, box.y2 - box.y1)
```

Observed with only this bug applied (`tests.test_1_image_matching.TestImageMatching.test_yolo_images`):

```
AssertionError: {'img[86 chars]tp': 0, 'fp': 1, 'fn': 1}, 'img-04': {'tp': 0,[248 chars]: 0}} != {'img[86 chars]tp': 1, 'fp': 0, 'fn': 0}, 'img-04': {'tp': 1,[248 chars]: 0}}
  {'img-01': {'fn': 0, 'fp': 0, 'tp': 1},
   'img-02': {'fn': 1, 'fp': 0, 'tp': 1},
-  'img-03': {'fn': 1, 'fp': 1, 'tp': 0},
?                   ^        ^        ^

+  'img-03': {'fn': 0, 'fp': 0, 'tp': 1},
?                ...
```

### B2: Shallow copy of the ground-truth pool

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 1 test_yolo_images: yolo-s shows FPs (fn 0) on every image detr-v2 matched (img-01, 02, 04, 06, 07, 08, and the truck on img-05). Test 2: yolo totals are (3, 7, 0, 0.3, 1.0, 0.462), auto_accept is `{'detr-v2': [], 'yolo-s': []}`, and best_model is 'detr-v2'. detr-v2's own counts stay correct.
- **Location:** `prelabel/matching.py` → `evaluate_model`
- **Why it fails:** dict() copies only the outer mapping. The per-image lists are still the loader's lists, so pool.pop() removes detr-v2's matches from the shared ground truth. yolo-s is then scored against what detr-v2 left over, and auto_accept (which checks gt[image]) sees emptied lists.
- **Unblocks:** Most of yolo-s in Test 1, both models' auto_accept, and best_model.

Fix:

```diff
-    unmatched = dict(ground_truth)
+    unmatched = {image: list(boxes) for image, boxes in ground_truth.items()}
```

Observed with only this bug applied (`tests.test_1_image_matching.TestImageMatching.test_yolo_images`):

```
AssertionError: {'img-01': {'tp': 0, 'fp': 1, 'fn': 0}, 'img-02': {'tp': 0,[326 chars]: 0}} != {'img-01': {'tp': 1, 'fp': 0, 'fn': 0}, 'img-02': {'tp': 1,[326 chars]: 0}}
- {'img-01': {'fn': 0, 'fp': 1, 'tp': 0},
?                            ^        ^

+ {'img-01': {'fn': 0, 'fp': 0, 'tp': 1},
?                            ^        ^

-  'img-02': {'fn': 0, 'fp': 1, 'tp': 0},
?                   ^ ...
```

### B3: IoU threshold made strict

- **Type:** off-by-one
- **Symptom:** Masked by B1. Once B1 is fixed: Test 1 test_yolo_images shows yolo-s img-03 as {tp 0, fp 1, fn 1}; Test 2 yolo totals are (9, 1, 3, 0.9, 0.75, 0.818) and img-03 is missing from yolo's auto_accept. best_model is still yolo-s.
- **Location:** `prelabel/matching.py` → `match_image`
- **Why it fails:** The spec matches at IoU >= 0.5. yolo-s's img-03 sign box covers exactly half of the ground truth (IoU 0.5) and is rejected by `>`.
- **Unblocks:** yolo-s img-03 in Test 1, plus yolo totals/auto_accept.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-            if overlap > IOU_THRESHOLD:
+            if overlap >= IOU_THRESHOLD:
```

Observed with only this bug applied (`tests.test_1_image_matching.TestImageMatching.test_yolo_images`):

```
AssertionError: {'img[86 chars]tp': 0, 'fp': 1, 'fn': 1}, 'img-04': {'tp': 1,[248 chars]: 0}} != {'img[86 chars]tp': 1, 'fp': 0, 'fn': 0}, 'img-04': {'tp': 1,[248 chars]: 0}}
  {'img-01': {'fn': 0, 'fp': 0, 'tp': 1},
   'img-02': {'fn': 1, 'fp': 0, 'tp': 1},
-  'img-03': {'fn': 1, 'fp': 1, 'tp': 0},
?                   ^        ^        ^

+  'img-03': {'fn': 0, 'fp': 0, 'tp': 1},
?                ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `prelabel/geometry.py` → `from_normalized_center`: The halving and the width/height scaling look easy to get backwards, but this is exactly the README formula for continuous pixel edges. No +1 is needed because edges are not inclusive pixel indices.
- `prelabel/matching.py` → `pick_best`: The key (iou, -index) looks odd, but max() then takes the highest IoU and, among equal IoUs, the smallest index, which is the earliest ground-truth box as rule 2 requires.
