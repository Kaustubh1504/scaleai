# set-005 answer key: Bounding-box QA: IoU matching and annotator recall

**Domain:** bbox_qa  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_image_review.TestImageReview.test_exact_box_is_a_match`
- `tests.test_1_image_review.TestImageReview.test_flagged_for_re_review`
- `tests.test_1_image_review.TestImageReview.test_per_image_counts`
- `tests.test_2_annotator_summary.TestAnnotatorSummary.test_images_reviewed`
- `tests.test_2_annotator_summary.TestAnnotatorSummary.test_summary`

## Bugs (recommended order)

### B1: Box area computed with exclusive coordinates

- **Type:** iou-inclusive-exclusive
- **Symptom:** Test 1: img_03/alice counts as a TP (recall 1.0) and is no longer flagged. Its dog box only half-overlaps the ground truth (true IoU 0.43). Test 2: alice shows tp 9, fp 0, fn 1.
- **Location:** `boxqa/geometry.py` → `area`
- **Why it fails:** The coordinates are inclusive, so a box covers x_max − x_min + 1 pixels. The intersection uses +1 but the area doesn't, so the union shrinks and IoU is inflated. For small boxes 0.43 becomes 0.59, which clears the 0.5 threshold.
- **Unblocks:** Test 1 img_03/alice and the flagged list.

Fix:

```diff
-    return (box.x_max - box.x_min) * (box.y_max - box.y_min)
+    return (box.x_max - box.x_min + 1) * (box.y_max - box.y_min + 1)
```

Observed with only this bug applied (`tests.test_1_image_review.TestImageReview.test_flagged_for_re_review`):

```
AssertionError: Lists differ: ['img[22 chars]', 'img_02/chen', 'img_04/alice', 'img_05/bob'] != ['img[22 chars]', 'img_02/chen', 'img_03/alice', 'img_04/alice', 'img_05/bob']

First differing element 3:
'img_04/alice'
'img_03/alice'

Second list contains 1 additional elements.
First extra element 5:
'img_05/bob'

- ['img_01/chen', 'img_02/bob', 'img_02/chen', 'img_04/alice', 'img_05/bob']
+ ['img_ ...
```

### B2: Matched-box sets shared across image/annotator pairs

- **Type:** state-not-reset
- **Symptom:** Test 1: the first pairs (img_01/alice, img_01/bob) are right, then counts drift into impossible values: img_03/bob shows tp 2, fp -1, fn -1, recall 2.0, and the flagged list comes back empty. Test 2: precision and recall go above 1.
- **Location:** `boxqa/evaluate.py` → `evaluate`
- **Why it fails:** matched_pred/matched_gt hold box indices, which restart at 0 for every image. Created once outside the loop, they keep indices from earlier pairs, so each pair's TP/FP/FN is computed from everything matched so far.
- **Unblocks:** Test 1 per-image counts, and most of Test 2.

Fix:

```diff
-    matched_pred, matched_gt = set(), set()
     for (image_id, annotator), preds in sorted(preds_by_key.items()):
         gts = gt_by_image.get(image_id, [])
+        matched_pred, matched_gt = set(), set()
```

Observed with only this bug applied (`tests.test_1_image_review.TestImageReview.test_exact_box_is_a_match`):

```
AssertionError: {'tp': 2, 'fp': -1, 'fn': -1, 'recall': 2.0} != {'tp': 1, 'fp': 0, 'fn': 0, 'recall': 1.0}
- {'fn': -1, 'fp': -1, 'recall': 2.0, 'tp': 2}
?        ^^        ^^            ^          ^

+ {'fn': 0, 'fp': 0, 'recall': 1.0, 'tp': 1}
?        ^        ^            ^          ^
```

### B3: groupby over unsorted results

- **Type:** groupby-misuse
- **Symptom:** Test 2 only: every annotator shows images: 1 with only their last image's numbers (alice = img_05 only, bob = img_06 only, chen = img_05 only).
- **Location:** `boxqa/reports.py` → `annotator_summary`
- **Why it fails:** itertools.groupby only groups consecutive items. Results are sorted by image first, so each annotator shows up in many short runs, and each run overwrites summary[annotator].
- **Unblocks:** Test 2.
- **Masked:** only surfaces in test_2_annotator_summary.

Fix:

```diff
-    for annotator, group in groupby(results, key=lambda r: r.annotator):
+    ordered = sorted(results, key=lambda r: r.annotator)
+    for annotator, group in groupby(ordered, key=lambda r: r.annotator):
```

Observed with only this bug applied (`tests.test_2_annotator_summary.TestAnnotatorSummary.test_images_reviewed`):

```
AssertionError: {'alice': 1, 'bob': 1, 'chen': 1} != {'alice': 5, 'bob': 6, 'chen': 4}
- {'alice': 1, 'bob': 1, 'chen': 1}
?           ^         ^          ^

+ {'alice': 5, 'bob': 6, 'chen': 4}
?           ^         ^          ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `boxqa/matching.py` → `greedy_match`: Sorting (-iou, i, j) ascending gives best IoU first, with ties going to the earlier annotator box and then the earlier ground-truth box, which is exactly the spec. The `>=` threshold is also the spec. It looks like the obvious place for a matching problem, but it has none.
- `boxqa/loader.py` → `within_cutoff`: `<=` keeps annotations submitted on the cutoff day, which the spec requires ('on or before'). Alice's img_05 rows are dated exactly 2026-05-10 and must count.
