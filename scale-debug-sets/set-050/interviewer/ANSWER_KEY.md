# set-050 answer key: Median consensus for 1-10 response ratings

**Domain:** annotation_consensus  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_cleaning.TestCleaning.test_1_rushed_counts` | B1 Duration read with timedelta.seconds |
| `test_1_cleaning.TestCleaning.test_2_resubmitted_item` | B2 Resubmissions deduped by submission id |
| `test_2_consensus.TestConsensus.test_3_consensus_values` | B3 Even-count median uses floor division |
| `test_2_consensus.TestConsensus.test_4_outlier_counts` | B4 Outliers removed while iterating the same list |
| `test_3_summary.TestSummary.test_5_category_means` | B5 Category total not reset per category |
| `test_3_summary.TestSummary.test_6_escalated_items` | B6 Enum status compared to a string |

## Failing pattern with all bugs present

- `tests.test_1_cleaning.TestCleaning.test_1_rushed_counts`
- `tests.test_1_cleaning.TestCleaning.test_2_resubmitted_item`
- `tests.test_2_consensus.TestConsensus.test_3_consensus_values`
- `tests.test_2_consensus.TestConsensus.test_4_outlier_counts`
- `tests.test_3_summary.TestSummary.test_5_category_means`
- `tests.test_3_summary.TestSummary.test_6_escalated_items`

## Bugs (recommended order)

### B1: Duration read with timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 1 test_1_rushed_counts: ann-07 shows 1 rushed submission ({'ann-07': 1, 'ann-08': 1, 'ann-10': 1} instead of {'ann-08': 1, 'ann-10': 1}). I-09's consensus and status do not change.
- **Location:** `ratingpanel/utils.py` → `duration_seconds`
- **Why it fails:** `.seconds` is only the seconds component of the timedelta, ignoring whole days. s-040 was open for 1 day and 12 seconds, so it reads as 12 seconds and is dropped as rushed.
- **Failing test:** `test_1_cleaning.TestCleaning.test_1_rushed_counts`
- **Unblocks:** test_1_rushed_counts

Fix:

```diff
-    return (finished_at - started_at).seconds
+    return (finished_at - started_at).total_seconds()
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_1_rushed_counts`):

```
AssertionError: {'ann-07': 1, 'ann-08': 1, 'ann-10': 1} != {'ann-08': 1, 'ann-10': 1}
- {'ann-07': 1, 'ann-08': 1, 'ann-10': 1}
?  -------------

+ {'ann-08': 1, 'ann-10': 1}
```

### B2: Resubmissions deduped by submission id

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_2_resubmitted_item: I-04 has agreement 0.8 instead of 1.0; status 'agreed' and consensus 7 are unchanged.
- **Location:** `ratingpanel/loader.py` → `latest_only`
- **Why it fails:** Submission ids are unique, so keying on them never collapses anything. ann-01's superseded 5 on I-04 stays alongside their later 7, which drops I-04's agreement to 0.8.
- **Failing test:** `test_1_cleaning.TestCleaning.test_2_resubmitted_item`
- **Unblocks:** test_2_resubmitted_item

Fix:

```diff
-        key = r.submission_id
+        key = (r.item_id, r.annotator_id)
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_2_resubmitted_item`):

```
AssertionError: {'status': 'agreed', 'consensus': 7, 'agreement': 0.8} != {'status': 'agreed', 'consensus': 7, 'agreement': 1.0}
- {'agreement': 0.8, 'consensus': 7, 'status': 'agreed'}
?                --

+ {'agreement': 1.0, 'consensus': 7, 'status': 'agreed'}
?               ++
```

### B3: Even-count median uses floor division

- **Type:** integer-division
- **Symptom:** Test 2 test_3_consensus_values: I-06's consensus is 6 instead of 6.5. Every other item matches.
- **Location:** `ratingpanel/scoring.py` → `median`
- **Why it fails:** With integer ratings, `//` floors the mean of the two middle values, so I-06 (6, 6, 7, 7) gets 6 instead of 6.5. Items whose middle pair has an even sum look fine.
- **Failing test:** `test_2_consensus.TestConsensus.test_3_consensus_values`
- **Unblocks:** test_3_consensus_values

Fix:

```diff
-    return (ordered[mid - 1] + ordered[mid]) // 2
+    return (ordered[mid - 1] + ordered[mid]) / 2
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_3_consensus_values`):

```
AssertionError: {'I-0[61 chars]6': 6, 'I-07': 5, 'I-08': 8, 'I-09': 6, 'I-10'[24 chars]None} != {'I-0[61 chars]6': 6.5, 'I-07': 5, 'I-08': 8, 'I-09': 6, 'I-1[26 chars]None}
  {'I-01': None,
   'I-02': 6,
   'I-03': 4,
   'I-04': 7,
   'I-05': None,
-  'I-06': 6,
+  'I-06': 6.5,
?           ++

   'I-07': 5,
   'I-08': 8,
   'I-09': 6,
   'I-10': 5,
   'I-11': 9,
   'I-12': None}
```

### B4: Outliers removed while iterating the same list

- **Type:** mutate-while-iterating
- **Symptom:** Test 2 test_4_outlier_counts: ann-05 is missing ({'ann-03': 1, 'ann-04': 1} instead of also 'ann-05': 1). I-08's consensus is still 8.
- **Location:** `ratingpanel/scoring.py` → `drop_outliers`
- **Why it fails:** Removing from the list being iterated shifts the next element into the current index, so the loop skips it. On I-08 the 2 and the 1 are adjacent; once the 2 is removed the 1 is never examined.
- **Failing test:** `test_2_consensus.TestConsensus.test_4_outlier_counts`
- **Unblocks:** test_4_outlier_counts

Fix:

```diff
-    for r in kept:
+    for r in list(kept):
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_4_outlier_counts`):

```
AssertionError: {'ann-03': 1, 'ann-04': 1} != {'ann-03': 1, 'ann-04': 1, 'ann-05': 1}
- {'ann-03': 1, 'ann-04': 1}
+ {'ann-03': 1, 'ann-04': 1, 'ann-05': 1}
?                         +++++++++++++
```

### B5: Category total not reset per category

- **Type:** state-not-reset
- **Symptom:** Test 3 test_5_category_means: writing is 18.83 instead of 6.67; coding (5.67) is right.
- **Location:** `ratingpanel/reports.py` → `category_means`
- **Why it fails:** The running total is created once, so each category's sum includes every category before it. coding (first) is right, writing includes coding and math.
- **Failing test:** `test_3_summary.TestSummary.test_5_category_means`
- **Unblocks:** test_5_category_means

Fix:

```diff
     means = {}
-    total = 0.0
     for cat in sorted(by_cat):
+        total = 0.0
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_5_category_means`):

```
AssertionError: {'coding': 5.67, 'writing': 18.83} != {'coding': 5.67, 'writing': 6.67}
- {'coding': 5.67, 'writing': 18.83}
?                             ^^ ^^

+ {'coding': 5.67, 'writing': 6.67}
?                             ^ ^^
```

### B6: Enum status compared to a string

- **Type:** enum-vs-string
- **Symptom:** Test 3 test_6_escalated_items: escalated is [] instead of ['I-02', 'I-10'], even though status_counts reports 2 escalated items.
- **Location:** `ratingpanel/reports.py` → `summarize`
- **Why it fails:** `res.status` is a Status enum member, and a plain Enum never equals its value string, so nothing matches and the list is empty. status_counts works because it uses `.value`.
- **Failing test:** `test_3_summary.TestSummary.test_6_escalated_items`
- **Unblocks:** test_6_escalated_items

Fix:

```diff
# ratingpanel/reports.py
-if res.status == "escalated"
+if res.status is Status.ESCALATED

# ratingpanel/reports.py
+from .models import Status
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_6_escalated_items`):

```
AssertionError: Lists differ: [] != ['I-02', 'I-10']

Second list contains 2 additional elements.
First extra element 0:
'I-02'

- []
+ ['I-02', 'I-10']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `ratingpanel/utils.py` → `parse_rating`: `int(float(text))` looks like it silently truncates, but the README says ratings are whole numbers sometimes written as `6.0`, so float-then-int is exactly what is needed; blanks and out-of-range values return None.
- `ratingpanel/scoring.py` → `agreement`: `<= 1` looks like it should be `< 1`, but the spec counts ratings within 1 point inclusive. It divides by the number of remaining ratings and rounds to 3 decimals as required.
