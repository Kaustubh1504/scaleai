# set-053 answer key: Pre-label review QA: survival of model boxes after human review

**Domain:** bbox_qa  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_outcomes.TestOutcomes.test_street_outcomes` | B1 Zero coordinate treated as blank |
| `test_1_outcomes.TestOutcomes.test_warehouse_outcomes` | B2 Pixel-inclusive +1 on continuous coordinates |
| `test_2_report.TestReport.test_out_of_bounds` | B3 Clipping mutates the reviewer's original boxes |

## Failing pattern with all bugs present

- `tests.test_1_outcomes.TestOutcomes.test_street_outcomes`
- `tests.test_1_outcomes.TestOutcomes.test_warehouse_outcomes`
- `tests.test_2_report.TestReport.test_out_of_bounds`

## Bugs (recommended order)

### B1: Zero coordinate treated as blank

- **Type:** falsy-zero
- **Symptom:** Test 1 test_street_outcomes: img-03/B5 is 'deleted' instead of 'accepted'. Everything else matches.
- **Location:** `prelabelqa/loader.py` → `load_reviews`
- **Why it fails:** all() treats 0.0 as false, so a review box touching the left edge (x_min = 0) is dropped as if a coordinate were blank. Its pre-label then has no reviewed box and shows as deleted.
- **Failing test:** `test_1_outcomes.TestOutcomes.test_street_outcomes`
- **Unblocks:** test_street_outcomes.

Fix:

```diff
-            if not all(coords):
+            if any(c is None for c in coords):
```

Observed with only this bug applied (`tests.test_1_outcomes.TestOutcomes.test_street_outcomes`):

```
AssertionError: {'img[106 chars]5': 'deleted', 'img-03/B6': 'accepted', 'img-0[39 chars]ted'} != {'img[106 chars]5': 'accepted', 'img-03/B6': 'accepted', 'img-[40 chars]ted'}
  {'img-01/B1': 'accepted',
   'img-01/B2': 'accepted',
   'img-02/B3': 'accepted',
   'img-02/B4': 'relabeled',
-  'img-03/B5': 'deleted',
?                ^ ^^

+  'img-03/B5': 'accepted',
?                ^^^ ^

   'img-03 ...
```

### B2: Pixel-inclusive +1 on continuous coordinates

- **Type:** iou-inclusive-exclusive
- **Symptom:** Test 1 test_warehouse_outcomes: img-05/B8 is 'accepted' instead of 'adjusted'. Every other outcome is unchanged.
- **Location:** `prelabelqa/geometry.py` → `span`
- **Why it fails:** The README defines continuous coordinates, so width is x_max − x_min. Adding 1 to every span inflates both the areas and the intersection, which pushes IoU toward 1. For the narrow B8 pallet that moves IoU from 0.897 to 0.902, over the 0.9 line.
- **Failing test:** `test_1_outcomes.TestOutcomes.test_warehouse_outcomes`
- **Unblocks:** test_warehouse_outcomes.

Fix:

```diff
-    return hi - lo + 1
+    return hi - lo
```

Observed with only this bug applied (`tests.test_1_outcomes.TestOutcomes.test_warehouse_outcomes`):

```
AssertionError: {'img-05/B8': 'accepted', 'img-05/B9': 'accepted', 'img-0[118 chars]ted'} != {'img-05/B8': 'adjusted', 'img-05/B9': 'accepted', 'img-0[118 chars]ted'}
- {'img-05/B8': 'accepted',
?                 ^^^^

+ {'img-05/B8': 'adjusted',
?                 ^^^^

   'img-05/B9': 'accepted',
   'img-06/B10': 'deleted',
   'img-06/B11': 'adjusted',
   'img-07/B12': 'accepted',
   'img-08/B13' ...
```

### B3: Clipping mutates the reviewer's original boxes

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 2 test_out_of_bounds: [] instead of [['img-01', None, 'sign'], ['img-09', 'B15', 'car']]. Outcomes and added counts are unaffected.
- **Location:** `prelabelqa/geometry.py` → `clip_to_image`
- **Why it fails:** copy.copy of a list makes a new list holding the same Box objects, so clipping changes the original reviewed boxes in place. By the time the out-of-bounds check reads the originals they've already been clipped, so nothing is out of bounds.
- **Failing test:** `test_2_report.TestReport.test_out_of_bounds`
- **Unblocks:** test_out_of_bounds.

Fix:

```diff
-    clipped = copy.copy(boxes)
+    clipped = copy.deepcopy(boxes)
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_out_of_bounds`):

```
AssertionError: Lists differ: [] != [['img-01', None, 'sign'], ['img-09', 'B15', 'car']]

Second list contains 2 additional elements.
First extra element 0:
['img-01', None, 'sign']

- []
+ [['img-01', None, 'sign'], ['img-09', 'B15', 'car']]
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `prelabelqa/geometry.py` → `is_out_of_bounds`: Strict comparisons are right for continuous coordinates: a box with x_max == width (img-05/B9 ends at 800) sits exactly on the edge and is inside, as the README says. `>=` would wrongly flag it.
