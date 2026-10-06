# set-096 answer key: Group-aware dataset splits with pins and dedupe

**Domain:** dataset_split  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_cleaning.TestCleaning.test_drop_reasons` | B1 Blocked samples removed while iterating |
| `test_1_cleaning.TestCleaning.test_duplicates` | B2 Duplicate original chosen by id before date |
| `test_2_assignment.TestAssignment.test_intent_groups` | B3 Deficit ties broken alphabetically |
| `test_2_assignment.TestAssignment.test_toxicity_groups` | B4 Pin keys trimmed but not lower-cased |
| `test_3_report.TestReport.test_targets` | B5 Shallow copy of defaults leaks fractions |
| `test_3_report.TestReport.test_label_totals` | B6 groupby over unsorted labels |

## Failing pattern with all bugs present

- `tests.test_1_cleaning.TestCleaning.test_drop_reasons`
- `tests.test_1_cleaning.TestCleaning.test_duplicates`
- `tests.test_2_assignment.TestAssignment.test_intent_groups`
- `tests.test_2_assignment.TestAssignment.test_toxicity_groups`
- `tests.test_3_report.TestReport.test_label_totals`
- `tests.test_3_report.TestReport.test_targets`

## Bugs (recommended order)

### B1: Blocked samples removed while iterating

- **Type:** mutate-while-iterating
- **Symptom:** Test 1 test_drop_reasons: TX-08 is reported as 'incomplete' instead of 'blocked_source'. Kept counts, duplicates and every split stay correct, because TX-08 is dropped either way.
- **Location:** `holdout/filters.py` → `drop_blocked`
- **Why it fails:** drop_blocked removes items from the list it is iterating over. After TX-07 is removed, the iterator steps past TX-08 (also from the proprietary tox-d04), so TX-08 survives this stage and is caught later by the blank-text rule, with the wrong reason.
- **Failing test:** `test_1_cleaning.TestCleaning.test_drop_reasons`
- **Unblocks:** test_1_cleaning.TestCleaning.test_drop_reasons

Fix:

```diff
-    for sample in samples:
+    for sample in list(samples):
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_drop_reasons`):

```
AssertionError: {'int[154 chars]8': 'incomplete', 'TX-14': 'low_quality', 'TX-[107 chars]ty'}} != {'int[154 chars]8': 'blocked_source', 'TX-14': 'low_quality', [111 chars]ty'}}
  {'intent': {'IN-05': 'blocked_source',
              'IN-09': 'low_quality',
              'IN-14': 'blocked_source',
              'IN-17': 'incomplete'},
   'summaries': {'SM-04': 'blocked_source',
                 'SM- ...
```

### B2: Duplicate original chosen by id before date

- **Type:** wrong-tie-break
- **Symptom:** Test 1 test_duplicates: intent reports IN-11 as a duplicate of IN-03; the original should be IN-11 (created 01/02/2026, earlier than IN-03). Toxicity and summaries come out right.
- **Location:** `holdout/dedupe.py` → `pick_original`
- **Why it fails:** pick_original's key is (sample_id, created), so the lowest id wins and the date only breaks ties. The spec makes the earliest date primary and the id the tie-break.
- **Failing test:** `test_1_cleaning.TestCleaning.test_duplicates`
- **Unblocks:** test_1_cleaning.TestCleaning.test_duplicates

Fix:

```diff
-    return min(copies, key=lambda s: (s.sample_id, s.created))
+    return min(copies, key=lambda s: (s.created, s.sample_id))
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_duplicates`):

```
AssertionError: {'intent': {'IN-11': 'IN-03'}, 'toxicity': {'TX-13': 'TX-[33 chars]01'}} != {'intent': {'IN-03': 'IN-11'}, 'toxicity': {'TX-13': 'TX-[33 chars]01'}}
- {'intent': {'IN-11': 'IN-03'},
+ {'intent': {'IN-03': 'IN-11'},
   'summaries': {'SM-11': 'SM-01'},
   'toxicity': {'TX-13': 'TX-09'}}
```

### B3: Deficit ties broken alphabetically

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_intent_groups: in-d04 goes to val, in-d05 to train, in-d06 to val and in-d07 to train; expected train/val/train/val. Toxicity and summaries are unaffected.
- **Location:** `holdout/allocator.py` → `choose_split`
- **Why it fails:** choose_split's key is (deficit, split name), so on equal deficits the alphabetically largest name ('val') wins over 'train'. The spec prefers train, then val, then test. Intent is the only dataset that reaches a train/val tie (deficit 3 and 3 when in-d04 is placed), and the change ripples through the rest of the assignment.
- **Failing test:** `test_2_assignment.TestAssignment.test_intent_groups`
- **Unblocks:** test_2_assignment.TestAssignment.test_intent_groups

Fix:

```diff
-    return max(SPLITS, key=lambda split: (deficit[split], split))
+    return max(SPLITS, key=lambda split: deficit[split])
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_intent_groups`):

```
AssertionError: {'in-[58 chars]4': 'val', 'in-d05': 'train', 'in-d06': 'val',[14 chars]ain'} != {'in-[58 chars]4': 'train', 'in-d05': 'val', 'in-d06': 'train[14 chars]val'}
  {'in-d01': 'train',
   'in-d02': 'test',
   'in-d03': 'train',
-  'in-d04': 'val',
-  'in-d05': 'train',
?        ^

+  'in-d04': 'train',
?        ^

-  'in-d06': 'val',
?        ^

+  'in-d05': 'val',
?        ^

-  'in-d07 ...
```

### B4: Pin keys trimmed but not lower-cased

- **Type:** id-normalization
- **Symptom:** Test 2 test_toxicity_groups: tox-d05 lands in val instead of its pinned test split, and tox-d02, tox-d03 and tox-d06 shift as a result. The intent pin still works.
- **Location:** `holdout/config.py` → `load_datasets`
- **Why it fails:** Pin keys are only trimmed, so the toxicity pin is stored under 'TOX-D05' while sample document ids are lower-cased to 'tox-d05'. The lookup misses and the document is allocated like any other.
- **Failing test:** `test_2_assignment.TestAssignment.test_toxicity_groups`
- **Unblocks:** test_2_assignment.TestAssignment.test_toxicity_groups

Fix:

```diff
-            pins={textnorm.clean(doc): textnorm.clean(split).lower()
+            pins={textnorm.norm_doc(doc): textnorm.clean(split).lower()
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_toxicity_groups`):

```
AssertionError: {'tox[24 chars]': 'test', 'tox-d03': 'train', 'tox-d05': 'val[54 chars]est'} != {'tox[24 chars]': 'train', 'tox-d03': 'val', 'tox-d05': 'test[53 chars]est'}
  {'tox-d01': 'train',
-  'tox-d02': 'test',
-  'tox-d03': 'train',
?         ^

+  'tox-d02': 'train',
?         ^

-  'tox-d05': 'val',
?         ^

+  'tox-d03': 'val',
?         ^

+  'tox-d05': 'test',
-  'tox-d06': 'train ...
```

### B5: Shallow copy of defaults leaks fractions

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 3 test_targets: summaries gets train 7 / val 2 / test 3 instead of 8 / 2 / 2. Intent and toxicity targets are right.
- **Location:** `holdout/config.py` → `merge`
- **Why it fails:** copy.copy makes a shallow copy, so every merged config shares the defaults' nested `fractions` dict. When toxicity merges its own test: 30, it writes into the shared defaults, and summaries (processed later, with no override) inherits 30%.
- **Failing test:** `test_3_report.TestReport.test_targets`
- **Unblocks:** test_3_report.TestReport.test_targets

Fix:

```diff
-    merged = copy.copy(defaults)
+    merged = copy.deepcopy(defaults)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_targets`):

```
AssertionError: {'int[73 chars] 4, 'test': 6}, 'summaries': {'train': 7, 'val': 2, 'test': 3}} != {'int[73 chars] 4, 'test': 6}, 'summaries': {'train': 8, 'val': 2, 'test': 2}}
  {'intent': {'test': 3, 'train': 9, 'val': 3},
-  'summaries': {'test': 3, 'train': 7, 'val': 2},
?                        ^           ^

+  'summaries': {'test': 2, 'train': 8, 'val': 2},
?                        ^        ...
```

### B6: groupby over unsorted labels

- **Type:** groupby-misuse
- **Symptom:** Test 3 test_label_totals: every dataset's counts are too small, e.g. intent gives book_flight 1, refund 2, cancel 1, greet 1 instead of 4/4/2/5.
- **Location:** `holdout/reports.py` → `label_totals`
- **Why it fails:** itertools.groupby only groups consecutive equal keys. Without sorting by label first, each label appears in several runs, and the dict comprehension keeps only the length of the last run for each label.
- **Failing test:** `test_3_report.TestReport.test_label_totals`
- **Unblocks:** test_3_report.TestReport.test_label_totals

Fix:

```diff
-    ordered = list(samples)
+    ordered = sorted(samples, key=lambda s: s.label)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_label_totals`):

```
AssertionError: {'int[17 chars]ht': 1, 'refund': 2, 'cancel': 1, 'greet': 1},[112 chars]: 1}} != {'int[17 chars]ht': 4, 'cancel': 4, 'greet': 2, 'refund': 5},[112 chars]: 3}}
Diff is 770 characters long. Set self.maxDiff to None to see it.
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `holdout/allocator.py` → `compute_targets`: The `//` looks like an integer-division slip, but rule 6 asks for floor(n x pct / 100) with whole-number percentages, so multiplying first and floor-dividing by 100 is exact. Train takes the remainder, so the targets always add up to n.
- `holdout/textnorm.py` → `fingerprint`: Stripping every non-word, non-space character looks aggressive, but rule 4 says duplicates match ignoring case, punctuation and runs of whitespace. Lower-casing, removing punctuation and re-joining on single spaces is exactly that.
