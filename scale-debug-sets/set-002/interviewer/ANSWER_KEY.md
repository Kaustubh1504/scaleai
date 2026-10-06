# set-002 answer key: Gold-weighted annotation consensus

**Domain:** annotation_consensus  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_annotator_quality.TestAnnotatorQuality.test_blocked_annotators`
- `tests.test_1_annotator_quality.TestAnnotatorQuality.test_only_active_annotators_listed`
- `tests.test_1_annotator_quality.TestAnnotatorQuality.test_quality_table`
- `tests.test_2_consensus.TestConsensus.test_full_consensus`
- `tests.test_2_consensus.TestConsensus.test_labels`
- `tests.test_3_summary.TestSummary.test_label_counts`
- `tests.test_3_summary.TestSummary.test_most_disputed`
- `tests.test_3_summary.TestSummary.test_needs_more_votes`

## Bugs (recommended order)

### B1: "false"/"no" strings parsed as active

- **Type:** bool-from-string
- **Symptom:** Test 1: ann-08 and ann-09 appear in the quality table even though they are inactive. Test 2: their votes change T05 (confidence 0.667 instead of 1.0) and resolve T08, which should need more votes.
- **Location:** `consensus/utils.py` → `parse_bool`
- **Why it fails:** bool() of any non-empty string is True, so "false" and "no" both become active. Only real JSON booleans and numbers survive bool().
- **Unblocks:** Test 1 table membership, plus T05/T08 in Test 2.

Fix:

```diff
+    if isinstance(value, str):
+        return value.strip().lower() in {"true", "yes", "y", "1"}
     return bool(value)
```

Observed with only this bug applied (`tests.test_1_annotator_quality.TestAnnotatorQuality.test_only_active_annotators_listed`):

```
AssertionError: Lists differ: ['ann[22 chars]3', 'ann-04', 'ann-05', 'ann-06', 'ann-07', 'ann-08', 'ann-09'] != ['ann[22 chars]3', 'ann-04', 'ann-05', 'ann-06', 'ann-07']

First list contains 2 additional elements.
First extra element 7:
'ann-08'

+ ['ann-01', 'ann-02', 'ann-03', 'ann-04', 'ann-05', 'ann-06', 'ann-07']
- ['ann-01',
-  'ann-02',
-  'ann-03',
-  'ann-04',
-  'ann-05',
-  'ann-06',
- ...
```

### B2: Annotation annotator ids not lower-cased

- **Type:** id-normalization
- **Symptom:** Test 1: ann-05 shows accuracy 0.5, gold_answered 0, not blocked. It should be 0.0 / 2 / blocked. Consensus doesn't change, because a blocked annotator's votes don't count either way.
- **Location:** `consensus/loader.py` → `read_annotations`
- **Why it fails:** Registry ids are lower-cased, but annotation ids are only trimmed. Every 'ANN-05'/'Ann-05' row fails the registry lookup and is dropped as unknown, so ann-05 looks as if they never answered gold.
- **Unblocks:** Test 1 row for ann-05, and it exposes B3.

Fix:

```diff
-                annotator_id=clean(row["annotator_id"]),
+                annotator_id=norm_annotator(row["annotator_id"]),
```

Observed with only this bug applied (`tests.test_1_annotator_quality.TestAnnotatorQuality.test_blocked_annotators`):

```
AssertionError: Lists differ: [] != ['ann-05']

Second list contains 1 additional elements.
First extra element 0:
'ann-05'

- []
+ ['ann-05']
```

### B3: Zero accuracy replaced by the prior

- **Type:** falsy-zero
- **Symptom:** Only visible after B2 is fixed. ann-05 shows accuracy 0.5 with gold_answered 2 and is not blocked. In Test 2, T04 drops to confidence 0.75 and T09 to 0.833.
- **Location:** `consensus/gold.py` → `quality_table`
- **Why it fails:** `x or PRIOR` treats a real 0.0 accuracy as missing, so a fully wrong annotator gets the 0.5 prior and keeps voting.
- **Unblocks:** Test 1 (ann-05), and T04/T09 in Test 2.
- **Masked:** invisible until B2 is fixed (identical test output either way).

Fix:

```diff
-accuracy=rates.get(aid) or PRIOR
+accuracy=rates.get(aid, PRIOR)
```

Observed with only this bug applied (`tests.test_1_annotator_quality.TestAnnotatorQuality.test_blocked_annotators`):

```
AssertionError: Lists differ: [] != ['ann-05']

Second list contains 1 additional elements.
First extra element 0:
'ann-05'

- []
+ ['ann-05']
```

### B4: Exactly 0.5 accuracy blocked

- **Type:** off-by-one
- **Symptom:** Test 1: ann-03, ann-04 and ann-06 (all exactly 0.5) are blocked. Test 2: T03, T04, T06, T07 and T10 all fall to needs_more_votes. Test 3: most_disputed becomes T05.
- **Location:** `consensus/voting.py` → `is_blocked`
- **Why it fails:** The spec blocks accuracy strictly below 0.5. `<=` also blocks the boundary, which includes every annotator still on the 0.5 prior.
- **Unblocks:** Test 1 blocked flags. Much of Test 2 recovers.

Fix:

```diff
-    return row.accuracy <= MIN_ACCURACY
+    return row.accuracy < MIN_ACCURACY
```

Observed with only this bug applied (`tests.test_1_annotator_quality.TestAnnotatorQuality.test_blocked_annotators`):

```
AssertionError: Lists differ: ['ann-03', 'ann-04', 'ann-05', 'ann-06'] != ['ann-05']

First differing element 0:
'ann-03'
'ann-05'

First list contains 3 additional elements.
First extra element 1:
'ann-04'

- ['ann-03', 'ann-04', 'ann-05', 'ann-06']
+ ['ann-05']
```

### B5: Weight ties resolved by insertion order

- **Type:** wrong-tie-break
- **Symptom:** Test 2: T03 resolves to 'dog' and T07 to 'dog'. Both should be 'cat', since both are exact weight ties. T10 happens to come out right.
- **Location:** `consensus/voting.py` → `pick_winner`
- **Why it fails:** max() returns the first label that reaches the top weight, and that is whichever label was voted first. The spec breaks ties alphabetically.
- **Unblocks:** Test 2 labels for T03/T07, and the Test 3 label counts.

Fix:

```diff
-    return max(totals, key=totals.get)
+    return min(totals, key=lambda label: (-totals[label], label))
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_full_consensus`):

```
AssertionError: {'T03[31 chars]l': 'dog', 'confidence': 0.5, 'votes': 3}, 'T0[637 chars]: 0}} != {'T03[31 chars]l': 'cat', 'confidence': 0.5, 'votes': 3}, 'T0[637 chars]: 0}}
- {'T03': {'confidence': 0.5, 'label': 'dog', 'status': 'resolved', 'votes': 3},
?                                       ^^^

+ {'T03': {'confidence': 0.5, 'label': 'cat', 'status': 'resolved', 'votes': 3},
?                  ...
```

### B6: Label counts include unresolved tasks

- **Type:** counting-wrong-subset
- **Symptom:** Test 3 only: label_counts has an extra `None: 2` entry, from the two needs_more_votes tasks.
- **Location:** `consensus/reports.py` → `summarize`
- **Why it fails:** The count runs over every result instead of the resolved subset, so tasks without a label are counted under None.
- **Unblocks:** Test 3.
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-    counts = Counter(r.label for r in results.values())
+    counts = Counter(r.label for r in resolved)
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_label_counts`):

```
AssertionError: {'cat': 2, 'dog': 1, 'bird': 2, 'fish': 2, None: 2} != {'bird': 2, 'cat': 2, 'dog': 1, 'fish': 2}
- {None: 2, 'bird': 2, 'cat': 2, 'dog': 1, 'fish': 2}
?  ---------

+ {'bird': 2, 'cat': 2, 'dog': 1, 'fish': 2}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `consensus/loader.py` → `latest_submissions`: The `>=` looks like it should be `>`, but the spec says that on equal timestamps the later row in the file wins, so a later row with the same time has to replace the earlier one. It compares parsed datetimes, so the mixed formats sort correctly.
- `consensus/utils.py` → `parse_timestamp`: It covers exactly the three formats the README lists, with month/day order for the slash format.
