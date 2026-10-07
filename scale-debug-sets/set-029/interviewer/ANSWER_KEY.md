# set-029 answer key: Box audit: xywh predictions, per-class thresholds, greedy matching

**Domain:** bbox_qa  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_matching.TestMatching.test_matches` | B1 Matching takes the weakest overlap first |
| `test_2_report.TestReport.test_annotator_scores` | B2 Annotator ids not lower-cased |
| `test_2_report.TestReport.test_localization` | B3 Pixel-inclusive +1 in the intersection |

## Failing pattern with all bugs present

- `tests.test_1_matching.TestMatching.test_matches`
- `tests.test_2_report.TestReport.test_annotator_scores`
- `tests.test_2_report.TestReport.test_localization`

## Bugs (recommended order)

### B1: Matching takes the weakest overlap first

- **Type:** sort-direction
- **Symptom:** test_1 test_matches fails: on IMG-1 the pairs come out p01→g02, p02→g01, p03→g02 instead of p01→g01, p02→g02, p03→g01. All other pairs, the unmatched list and the annotator scores are unaffected.
- **Location:** `boxaudit/matching.py` → `match`
- **Why it fails:** Greedy matching has to start with the best overlap. In ascending order the weakest qualifying pair claims a box first. On IMG-1, ann-1's p02→g01 (0.720) gets accepted before p02→g02 (0.933), so p01 and p02 swap targets, and Ann-2's p03 lands on g02 (0.661) instead of g01 (0.960). Every prediction that matched still matches, so the unmatched list and the scores don't change.
- **Failing test:** `test_1_matching.TestMatching.test_matches`
- **Unblocks:** test_1 test_matches.

Fix:

```diff
-sorted(candidates(preds, gts), key=lambda c: c[0])
+sorted(candidates(preds, gts), key=lambda c: c[0], reverse=True)
```

Observed with only this bug applied (`tests.test_1_matching.TestMatching.test_matches`):

```
AssertionError: {'p01': 'g02', 'p02': 'g01', 'p03': 'g02', 'p04': 'g[181 chars]g09'} != {'p01': 'g01', 'p02': 'g02', 'p03': 'g01', 'p04': 'g[181 chars]g09'}
- {'p01': 'g02',
?            ^

+ {'p01': 'g01',
?            ^

-  'p02': 'g01',
?            ^

+  'p02': 'g02',
?            ^

-  'p03': 'g02',
?            ^

+  'p03': 'g01',
?            ^

   'p04': 'g03',
   'p05': 'g04',
   'p06': ' ...
```

### B2: Annotator ids not lower-cased

- **Type:** id-normalization
- **Symptom:** test_2 test_annotator_scores fails: the report lists five annotators, including 'ANN-3' (tp 1, fp 1, fn 9) and 'Ann-2' (tp 1, fp 0, fn 9), and ann-2/ann-3 drop to tp 4 and tp 3 (f1 0.471 and 0.429). Matches are unchanged.
- **Location:** `boxaudit/loader.py` → `load_predictions`
- **Why it fails:** The IMG-2 rows are exported as 'ANN-3' and IMG-1's p03 as 'Ann-2'. Without lower-casing they become separate annotators, and each one is charged with every ground-truth box as a possible miss.
- **Failing test:** `test_2_report.TestReport.test_annotator_scores`
- **Unblocks:** test_2 test_annotator_scores.

Fix:

```diff
-                annotator=clean(row["annotator"]),
+                annotator=clean(row["annotator"]).lower(),
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_annotator_scores`):

```
AssertionError: {'ANN-3': {'tp': 1, 'fp': 1, 'fn': 9, 'prec[375 chars]429}} != {'ann-1': {'tp': 8, 'fp': 0, 'fn': 2, 'prec[206 chars]0.5}}
- {'ANN-3': {'f1': 0.167,
-            'fn': 9,
-            'fp': 1,
-            'precision': 0.5,
-            'recall': 0.1,
-            'tp': 1},
-  'Ann-2': {'f1': 0.182,
-            'fn': 9,
-            'fp': 0,
-            'precision': 1.0,
-        ...
```

### B3: Pixel-inclusive +1 in the intersection

- **Type:** iou-inclusive-exclusive
- **Symptom:** test_2 test_localization fails: {'car': 1.0, 'person': 0.984, 'sign': 0.776} instead of {'car': 0.971, 'person': 0.944, 'sign': 0.701}. Every class reads high, and matches and scores are unchanged.
- **Location:** `boxaudit/geometry.py` → `iou`
- **Why it fails:** The +1 belongs to inclusive pixel indexing. Here x2 is exclusive and area() has no +1, so the intersection is inflated against the union: exact matches score above 1 and every overlap reads high. No pair crosses a threshold, so matching is unchanged.
- **Failing test:** `test_2_report.TestReport.test_localization`
- **Unblocks:** test_2 test_localization.

Fix:

```diff
-    iw = min(a.x2, b.x2) - max(a.x1, b.x1) + 1
-    ih = min(a.y2, b.y2) - max(a.y1, b.y1) + 1
+    iw = min(a.x2, b.x2) - max(a.x1, b.x1)
+    ih = min(a.y2, b.y2) - max(a.y1, b.y1)
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_localization`):

```
AssertionError: {'car': 1.0, 'person': 0.984, 'sign': 0.776} != {'car': 0.971, 'person': 0.944, 'sign': 0.701}
- {'car': 1.0, 'person': 0.984, 'sign': 0.776}
?          --               ^              ^^

+ {'car': 0.971, 'person': 0.944, 'sign': 0.701}
?         ++++                ^              ^^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `boxaudit/matching.py` → `best_iou_per_gt`: Pooling every annotator's predictions looks like a scoping slip, but the README defines localisation as the best IoU any annotator reaches, ignoring thresholds and matching. max(..., default=0.0) covers boxes nobody predicted (g10).
- `boxaudit/loader.py` → `xywh_to_xyxy`: With exclusive right/bottom edges, x2 = x + w exactly. No ±1 is needed in this convention.
