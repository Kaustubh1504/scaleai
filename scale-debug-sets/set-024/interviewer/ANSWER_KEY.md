# set-024 answer key: Leak-free train/val/test split of labeled feedback

**Domain:** dataset_split  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_cleaning.TestCleaning.test_excluded_rows` | B1 Any non-blank consent string counts as consent |
| `test_1_cleaning.TestCleaning.test_duplicate_rows` | B2 Duplicate tie on created date not broken by item id |
| `test_2_splits.TestSplits.test_doc_assignment` | B3 doc_id not lower-cased |
| `test_2_splits.TestSplits.test_val_sample` | B4 Validation sample takes cap + 1 per label |
| `test_3_split_report.TestSplitReport.test_test_split_labels` | B5 Label tally shares a default dict |
| `test_3_split_report.TestSplitReport.test_test_split_avg_tokens` | B6 Token total not reset per split |

## Failing pattern with all bugs present

- `tests.test_1_cleaning.TestCleaning.test_duplicate_rows`
- `tests.test_1_cleaning.TestCleaning.test_excluded_rows`
- `tests.test_2_splits.TestSplits.test_doc_assignment`
- `tests.test_2_splits.TestSplits.test_val_sample`
- `tests.test_3_split_report.TestSplitReport.test_test_split_avg_tokens`
- `tests.test_3_split_report.TestSplitReport.test_test_split_labels`

## Bugs (recommended order)

### B1: Any non-blank consent string counts as consent

- **Type:** bool-from-string
- **Symptom:** test_excluded_rows fails: excluded is ['I018', 'I022'] instead of ['I013', 'I018', 'I022', 'I026']; the withdrawn-consent rows are kept.
- **Location:** `splitkit/utils.py` → `parse_bool`
- **Why it fails:** bool() of any non-empty string is True, so 'no' (I013) and 'false' (I026) read as consent given, and those rows stay in train.
- **Failing test:** `test_1_cleaning.TestCleaning.test_excluded_rows`
- **Unblocks:** test_excluded_rows

Fix:

```diff
-    return bool(text)
+    return text in {"y", "yes", "true", "1"}
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_excluded_rows`):

```
AssertionError: Lists differ: ['I018', 'I022'] != ['I013', 'I018', 'I022', 'I026']

First differing element 0:
'I018'
'I013'

Second list contains 2 additional elements.
First extra element 2:
'I022'

- ['I018', 'I022']
+ ['I013', 'I018', 'I022', 'I026']
```

### B2: Duplicate tie on created date not broken by item id

- **Type:** wrong-tie-break
- **Symptom:** test_duplicate_rows fails: duplicate is ['I012', 'I016'] instead of ['I012', 'I030'].
- **Location:** `splitkit/dedupe.py` → `pick_keeper`
- **Why it fails:** I030 and I016 share created = 2026-01-15. Without item_id in the key, min() returns the first in file order (I030), so I016 is dropped instead of I030.
- **Failing test:** `test_1_cleaning.TestCleaning.test_duplicate_rows`
- **Unblocks:** test_duplicate_rows

Fix:

```diff
-    return min(group, key=lambda it: it.created)
+    return min(group, key=lambda it: (it.created, it.item_id))
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_duplicate_rows`):

```
AssertionError: Lists differ: ['I012', 'I016'] != ['I012', 'I030']

First differing element 1:
'I016'
'I030'

- ['I012', 'I016']
?             ^^

+ ['I012', 'I030']
?             ^^
```

### B3: doc_id not lower-cased

- **Type:** id-normalization
- **Symptom:** test_doc_assignment fails: doc_splits has extra keys 'DOC-01' and 'Doc-08' (both train) next to the normal doc ids.
- **Location:** `splitkit/loader.py` → `load_items`
- **Why it fails:** 'DOC-01' and 'Doc-08' become documents of their own, with their own MD5 buckets. Their rows are no longer tied to doc-01/doc-08, which is exactly how group leakage happens; here they happen to hash into train too.
- **Failing test:** `test_2_splits.TestSplits.test_doc_assignment`
- **Unblocks:** test_doc_assignment

Fix:

```diff
-                doc_id=clean(row["doc_id"]),
+                doc_id=clean(row["doc_id"]).lower(),
```

Observed with only this bug applied (`tests.test_2_splits.TestSplits.test_doc_assignment`):

```
AssertionError: {'DOC-01': 'train', 'Doc-08': 'train', 'doc[208 chars]ain'} != {'doc-01': 'train', 'doc-02': 'val', 'doc-0[170 chars]ain'}
- {'DOC-01': 'train',
-  'Doc-08': 'train',
-  'doc-01': 'train',
? ^

+ {'doc-01': 'train',
? ^

   'doc-02': 'val',
   'doc-03': 'val',
   'doc-04': 'train',
   'doc-05': 'test',
   'doc-06': 'val',
   'doc-07': 'train',
   'doc-08': 'train',
   'doc-09': 'te ...
```

### B4: Validation sample takes cap + 1 per label

- **Type:** off-by-one
- **Symptom:** test_val_sample fails: negative gets ['I005', 'I010', 'I031'] and positive ['I004', 'I006', 'I007'], three each instead of two. neutral is unchanged.
- **Location:** `splitkit/sampler.py` → `val_sample`
- **Why it fails:** With `<=` a label still accepts an item when it already has `cap` items, so negative and positive get three each. neutral only has two val rows, so it looks right.
- **Failing test:** `test_2_splits.TestSplits.test_val_sample`
- **Unblocks:** test_val_sample

Fix:

```diff
-        if len(bucket) <= cap:
+        if len(bucket) < cap:
```

Observed with only this bug applied (`tests.test_2_splits.TestSplits.test_val_sample`):

```
AssertionError: {'neg[18 chars]I010', 'I031'], 'neutral': ['I008', 'I029'], '[31 chars]07']} != {'neg[18 chars]I010'], 'neutral': ['I008', 'I029'], 'positive[15 chars]06']}
- {'negative': ['I005', 'I010', 'I031'],
?                             --------

+ {'negative': ['I005', 'I010'],
   'neutral': ['I008', 'I029'],
-  'positive': ['I004', 'I006', 'I007']}
?                             --------

 ...
```

### B5: Label tally shares a default dict

- **Type:** mutable-default
- **Symptom:** test_test_split_labels fails: the test split's labels come out as large accumulated counts (e.g. {'negative': 27, 'neutral': 24, 'positive': 36} in a full run) instead of 2/2/2. The exact numbers depend on how many reports were built earlier in the process.
- **Location:** `splitkit/stats.py` → `tally`
- **Why it fails:** The `{}` default is created once and reused by every call, so the test split's counts include everything tallied before (train, val and earlier report builds). The `is None` check never fires.
- **Failing test:** `test_3_split_report.TestSplitReport.test_test_split_labels`
- **Unblocks:** test_test_split_labels

Fix:

```diff
-def tally(labels, counts={}):
+def tally(labels, counts=None):
```

Observed with only this bug applied (`tests.test_3_split_report.TestSplitReport.test_test_split_labels`):

```
AssertionError: {'negative': 27, 'neutral': 24, 'positive': 36} != {'negative': 2, 'neutral': 2, 'positive': 2}
- {'negative': 27, 'neutral': 24, 'positive': 36}
?               -              -              ^^

+ {'negative': 2, 'neutral': 2, 'positive': 2}
?                                           ^
```

### B6: Token total not reset per split

- **Type:** state-not-reset
- **Symptom:** test_test_split_avg_tokens fails: 18.83 instead of 4.83.
- **Location:** `splitkit/reports.py` → `split_stats`
- **Why it fails:** The running token total starts once, before the loop, so each split's average includes the words of every split before it. test, computed last, divides the whole dataset's words by its own 6 rows.
- **Failing test:** `test_3_split_report.TestSplitReport.test_test_split_avg_tokens`
- **Unblocks:** test_test_split_avg_tokens

Fix:

```diff
-    tokens = 0
     for split in SPLITS:
         members = by_split[split]
+        tokens = 0
```

Observed with only this bug applied (`tests.test_3_split_report.TestSplitReport.test_test_split_avg_tokens`):

```
AssertionError: 18.83 != 4.83
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `splitkit/splitter.py` → `split_for`: The `< 70` / `< 85` boundaries look like they could be off by one, but buckets 0-69 are exactly 70 values for train, 70-84 are 15 for val and 85-99 are 15 for test, as rule 5 says. Pinned docs are checked first.
- `splitkit/utils.py` → `parse_date`: It handles exactly the three README formats, with month/day/year for the slash format, and returns a date so comparisons across formats work.
