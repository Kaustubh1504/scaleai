# set-074 answer key: Rubric-calibrated Likert consensus

**Domain:** annotation_consensus  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_calibration.TestCalibration.test_bias_table`
- `tests.test_2_consensus.TestConsensus.test_full_consensus`
- `tests.test_2_consensus.TestConsensus.test_scores`
- `tests.test_2_consensus.TestConsensus.test_vote_counts`
- `tests.test_3_summary.TestSummary.test_by_rubric`
- `tests.test_3_summary.TestSummary.test_contested`

## Bugs (recommended order)

### B1: Ratings on the closing day dropped

- **Type:** time-window-boundary
- **Symptom:** Test 1: a08's v2 bias is 0.0 instead of -2.0. Test 2: I12 has 0 votes and I10 has 2 (both insufficient), and I02/I08 scores shift (2.25, 3.5) because a08's v2 lean is no longer removed. Test 3: v2 shows 2 insufficient and I08 becomes contested.
- **Location:** `likert/loader.py` → `counting_ratings`
- **Why it fails:** The window includes the whole closing day. `<` on the date drops every rating from 2026-06-14, including a08's only v2 gold rating and all of I12's ratings.
- **Unblocks:** Test 1 (a08 v2) and the I10/I12 rows in Test 2.

Fix:

```diff
-        if not config["opens"] <= r.submitted_at.date() < config["closes"]:
+        if not config["opens"] <= r.submitted_at.date() <= config["closes"]:
```

Observed with only this bug applied (`tests.test_1_calibration.TestCalibration.test_bias_table`):

```
AssertionError: {'a01[183 chars] 'a07': {'v1': 0.0, 'v2': 1.0}, 'a08': {'v1': 0.0, 'v2': 0.0}} != {'a01[183 chars] 'a07': {'v1': 0.0, 'v2': 1.0}, 'a08': {'v1': 0.0, 'v2': -2.0}}
  {'a01': {'v1': 1.0, 'v2': 0.0},
   'a02': {'v1': 0.0, 'v2': 0.5},
   'a03': {'v1': -1.0, 'v2': -1.0},
   'a04': {'v1': 0.0, 'v2': 0.0},
   'a05': {'v1': 0.5, 'v2': 0.0},
   'a06': {'v1': 0.0, 'v2': 0.0},
   'a07': {'v1': ...
```

### B2: Bias pools gold from both rubrics

- **Type:** counting-wrong-subset
- **Symptom:** Test 1: each annotator has one blended bias for both rubrics (a01 0.5/0.5, a02 0.25/0.25, a05 0.333/0.333 ...). Test 2: most scores move (I02 2.208, I03 3.75 and contested, I06 4.542 ...). Test 3: contested becomes ['I03', 'I04', 'I08', 'I09', 'I10'].
- **Location:** `likert/calibration.py` → `compute_bias`
- **Why it fails:** The bias must come from that annotator's gold ratings of the same rubric. Pooling both rubrics gives one blended value per annotator (a01: 0.5 for both instead of 1.0 / 0.0).
- **Unblocks:** Test 1 bias table; it exposes B3.

Fix:

```diff
-    rows = [r for r in gold if r.annotator_id == annotator_id]
+    rows = [r for r in gold if r.annotator_id == annotator_id and items[r.item_id].rubric == rubric]
```

Observed with only this bug applied (`tests.test_1_calibration.TestCalibration.test_bias_table`):

```
AssertionError: {'a01': {'v1': 0.5, 'v2': 0.5}, 'a02': {'v1': 0.25, 'v2'[205 chars]667}} != {'a01': {'v1': 1.0, 'v2': 0.0}, 'a02': {'v1': 0.0, 'v2':[190 chars]2.0}}
- {'a01': {'v1': 0.5, 'v2': 0.5},
?                 --          ^

+ {'a01': {'v1': 1.0, 'v2': 0.0},
?                ++           ^

-  'a02': {'v1': 0.25, 'v2': 0.25},
?                  ^^          -

+  'a02': {'v1': 0.0, 'v2': 0.5 ...
```

### B3: Memo key ignores the rubric

- **Type:** cache-key-missing-param
- **Symptom:** Only visible after B2 is fixed. Test 1: v2 repeats the v1 value for annotators whose first rated item was v1 (a01 1.0/1.0, a02 0.0/0.0, a05 0.5/0.5). Test 2: I02 3.0, I06 4.5, I08 4.0, I10 2.5, I12 4.0. Test 3: contested becomes ['I04', 'I09', 'I10'].
- **Location:** `likert/calibration.py` → `bias_for`
- **Why it fails:** The memo is keyed by annotator only, so whichever rubric is computed first for an annotator is returned for the other rubric too. consensus.resolve walks items in file order, so most annotators get their first-seen rubric's bias for both.
- **Unblocks:** Test 1 bias table and the scores/agreements in Test 2.
- **Masked:** invisible until B2 is fixed (identical test output either way).

Fix:

```diff
-    return memo.get_or_compute(annotator_id, lambda: compute_bias(gold, items, annotator_id, rubric))
+    return memo.get_or_compute((annotator_id, rubric), lambda: compute_bias(gold, items, annotator_id, rubric))
```

Observed with only this bug applied (`tests.test_1_calibration.TestCalibration.test_bias_table`):

```
AssertionError: {'a01[16 chars]v2': 1.0}, 'a02': {'v1': 0.0, 'v2': 0.0}, 'a03[180 chars]2.0}} != {'a01[16 chars]v2': 0.0}, 'a02': {'v1': 0.0, 'v2': 0.5}, 'a03[179 chars]2.0}}
- {'a01': {'v1': 1.0, 'v2': 1.0},
?                           ^

+ {'a01': {'v1': 1.0, 'v2': 0.0},
?                           ^

-  'a02': {'v1': 0.0, 'v2': 0.0},
?                             ^

+  'a02': {'v1': 0.0, 'v2':  ...
```

### B4: Even-length median takes the upper pair

- **Type:** off-by-one
- **Symptom:** Test 2 only: every 4-vote item's score is too high (I02 3.0, I06 4.75, I07 4.25, I08 5.0, I09 3.75, I12 4.0). 3- and 5-vote items are unaffected, and statuses happen not to change.
- **Location:** `likert/aggregate.py` → `median`
- **Why it fails:** For an even count n, the two middle values are at n//2 - 1 and n//2. Using n//2 and n//2 + 1 averages the upper pair, which inflates every 4-vote median.
- **Unblocks:** Test 2 scores for the 4-vote items and the dependent agreement/status.

Fix:

```diff
-    return (ordered[mid] + ordered[mid + 1]) / 2
+    return (ordered[mid - 1] + ordered[mid]) / 2
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_full_consensus`):

```
AssertionError: {'I01[101 chars]re': 3.0, 'agreement': 1.0, 'votes': 4}, 'I03'[744 chars]: 4}} != {'I01[101 chars]re': 2.75, 'agreement': 1.0, 'votes': 4}, 'I03[745 chars]: 4}}
  {'I01': {'agreement': 1.0, 'score': 4.0, 'status': 'agreed', 'votes': 4},
-  'I02': {'agreement': 1.0, 'score': 3.0, 'status': 'agreed', 'votes': 4},
?                                     ^ ^

+  'I02': {'agreement': 1.0, ...
```

### B5: Agreement counter not reset per item

- **Type:** state-not-reset
- **Symptom:** Test 2: agreement keeps growing past 1.0 (I02 2.0, I03 2.2, ...) so nothing is contested. Test 3: contested is [] and by_rubric shows 0 contested for both rubrics.
- **Location:** `likert/consensus.py` → `resolve`
- **Why it fails:** `within` is set once before the loop, so each item's count adds on top of every earlier item's. Agreement climbs above 1.0 and nothing after I01 can be contested.
- **Unblocks:** Test 2 agreements/statuses and the Test 3 contested list.

Fix:

```diff
     results = {}
-    within = 0
     for item in items.values():
         if item.gold is not None:
             continue
+        within = 0
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_full_consensus`):

```
AssertionError: {'I01[120 chars]nt': 2.0, 'votes': 4}, 'I03': {'status': 'agre[716 chars]: 4}} != {'I01[120 chars]nt': 1.0, 'votes': 4}, 'I03': {'status': 'agre[726 chars]: 4}}
  {'I01': {'agreement': 1.0, 'score': 4.0, 'status': 'agreed', 'votes': 4},
-  'I02': {'agreement': 2.0, 'score': 2.75, 'status': 'agreed', 'votes': 4},
?                       ^

+  'I02': {'agreement': 1.0, 'score': 2.75, ...
```

### B6: groupby over unsorted results

- **Type:** groupby-misuse
- **Symptom:** Test 3 test_by_rubric only: v1 {'agreed': 0, 'contested': 0, 'insufficient': 1} and v2 {'agreed': 1, 'contested': 0, 'insufficient': 0}; only the last item of each rubric is counted.
- **Location:** `likert/reports.py` → `rubric_summary`
- **Why it fails:** itertools.groupby only groups consecutive equal keys. Items alternate v1/v2 in file order, so each run has length 1 and every later run overwrites summary[rubric]; only the last item of each rubric survives.
- **Unblocks:** Test 3 by_rubric.
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
+    ordered = sorted(results.values(), key=lambda r: r.rubric)
     summary = {}
-    for rubric, group in groupby(results.values(), key=lambda r: r.rubric):
+    for rubric, group in groupby(ordered, key=lambda r: r.rubric):
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_by_rubric`):

```
AssertionError: {'v1': {'agreed': 0, 'contested': 0, 'insufficient': 1}, 'v[48 chars]: 0}} != {'v1': {'agreed': 3, 'contested': 2, 'insufficient': 1}, 'v[48 chars]: 0}}
- {'v1': {'agreed': 0, 'contested': 0, 'insufficient': 1},
?                   ^               ^

+ {'v1': {'agreed': 3, 'contested': 2, 'insufficient': 1},
?                   ^               ^

-  'v2': {'agreed': 1, 'contested': ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `likert/utils.py` → `parse_submitted`: Epoch values look like they might be milliseconds, but the spec says epoch seconds, and fromtimestamp(..., tz=utc) followed by dropping tzinfo gives the naive UTC time that matches the text formats. The values decode to the same June 2026 window as the text timestamps.
- `likert/calibration.py` → `adjust`: Subtracting the bias looks backwards, but bias is mean(score - gold), so an annotator who rates high has a positive bias and score - bias pulls them back toward gold. The clamp keeps results on the 1-5 scale (I06: a03's 4 + 1 becomes 5).
