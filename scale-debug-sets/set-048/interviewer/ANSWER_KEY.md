# set-048 answer key: Group-aware stratified train/val/test splitter

**Domain:** dataset_split  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_cleaning.TestCleaning.test_duplicate_rows`
- `tests.test_1_cleaning.TestCleaning.test_excluded_rows`
- `tests.test_2_splits.TestSplits.test_every_group_assigned`
- `tests.test_2_splits.TestSplits.test_group_labels`
- `tests.test_2_splits.TestSplits.test_group_split`
- `tests.test_3_report.TestReport.test_capped`
- `tests.test_3_report.TestReport.test_label_counts`
- `tests.test_3_report.TestReport.test_split_members`

## Bugs (recommended order)

### B1: exclude flag parsed with bool()

- **Type:** bool-from-string
- **Symptom:** Test 1: excluded is ['S-004', 'S-010', 'S-014', 'S-016', 'S-019', 'S-036'] instead of ['S-010', 'S-036'], and duplicates is [] (the duplicate rows were excluded first). Test 3: S-004 and S-016 vanish from test/train, test has dog 3 instead of 4, and S-033 is no longer capped.
- **Location:** `splitkit/utils.py` → `parse_flag`
- **Why it fails:** csv gives strings, and bool() of any non-empty string is True, so `no`, `false` and `No` rows are excluded too. Only blank cells survive.
- **Unblocks:** Test 1 excluded list; S-004 and S-016 return to the splits in Test 3. It also exposes B2.

Fix:

```diff
+    if isinstance(value, str):
+        return value.strip().lower() in TRUE_WORDS
     return bool(value)
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_duplicate_rows`):

```
AssertionError: Lists differ: [] != ['S-014', 'S-019']

Second list contains 2 additional elements.
First extra element 0:
'S-014'

- []
+ ['S-014', 'S-019']
```

### B2: Duplicates detected on the raw id

- **Type:** id-normalization
- **Symptom:** Only visible once B1 is fixed. Test 1: duplicates is [] instead of ['S-014', 'S-019']. Test 2: g-10 becomes a dog group and moves from test to train (g-12 to train as well). Test 3: S-014 and S-019 show up twice and the capped list grows.
- **Location:** `splitkit/loader.py` → `load_samples`
- **Why it fails:** The seen-set is keyed by the trimmed but not upper-cased id, so `s-014` and ` s-019` don't match `S-014`/`S-019` and are kept a second time. The extra dog vote also turns g-10 into a dog group.
- **Unblocks:** Test 1 duplicates, g-10 in Test 2, train/test membership in Test 3.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-            key = clean(row["sample_id"])
+            key = sid
```

Observed with only this bug applied (`tests.test_1_cleaning.TestCleaning.test_duplicate_rows`):

```
AssertionError: Lists differ: [] != ['S-014', 'S-019']

Second list contains 2 additional elements.
First extra element 0:
'S-014'

- []
+ ['S-014', 'S-019']
```

### B3: groupby over unsorted samples

- **Type:** groupby-misuse
- **Symptom:** Test 2: g-07 is labelled 'dog' instead of 'cat'; the cat stratum shrinks, so g-02 moves to val and g-03 to train. Test 3: split members, capped list and label counts all shift.
- **Location:** `splitkit/strata.py` → `group_labels`
- **Why it fails:** itertools.groupby only groups adjacent items. g-07's rows are split into two runs (S-013/S-014, then S-033 much later), and the dict comprehension keeps the last run, so g-07's label becomes dog.
- **Unblocks:** Test 2 group_labels for g-07 and the cat/dog strata.

Fix:

```diff
-    by_group = list(samples)
+    by_group = sorted(samples, key=lambda s: s.group_id)
```

Observed with only this bug applied (`tests.test_2_splits.TestSplits.test_group_labels`):

```
AssertionError: {'g-0[90 chars]7': 'dog', 'g-08': 'dog', 'g-09': 'cat', 'g-10[98 chars]dog'} != {'g-0[90 chars]7': 'cat', 'g-08': 'dog', 'g-09': 'cat', 'g-10[98 chars]dog'}
  {'g-01': 'cat',
   'g-02': 'cat',
   'g-03': 'cat',
   'g-04': 'dog',
   'g-05': 'cat',
   'g-06': 'dog',
-  'g-07': 'dog',
?           ^^^

+  'g-07': 'cat',
?           ^^^

   'g-08': 'dog',
   'g-09': 'cat',
   'g-10': 'b ...
```

### B4: Majority tie resolved by first seen

- **Type:** wrong-tie-break
- **Symptom:** Test 2: g-10 is labelled 'dog' instead of 'bird'; g-10 moves from test to train and g-12 from val to train. Test 3: test has no bird sample and four extra train samples are capped.
- **Location:** `splitkit/strata.py` → `majority`
- **Why it fails:** most_common orders equal counts by first insertion, so g-10 (dog, bird) becomes dog. The spec breaks ties alphabetically, giving bird.
- **Unblocks:** Test 2 g-10 label and the bird/dog strata.

Fix:

```diff
-    return counts.most_common(1)[0][0]
+    return min(counts, key=lambda label: (-counts[label], label))
```

Observed with only this bug applied (`tests.test_2_splits.TestSplits.test_group_labels`):

```
AssertionError: {'g-0[135 chars]0': 'dog', 'g-11': 'cat', 'g-12': 'bird', 'g-1[52 chars]dog'} != {'g-0[135 chars]0': 'bird', 'g-11': 'cat', 'g-12': 'bird', 'g-[53 chars]dog'}
  {'g-01': 'cat',
   'g-02': 'cat',
   'g-03': 'cat',
   'g-04': 'dog',
   'g-05': 'cat',
   'g-06': 'dog',
   'g-07': 'cat',
   'g-08': 'dog',
   'g-09': 'cat',
-  'g-10': 'dog',
?            --

+  'g-10': 'bird',
?         ...
```

### B5: Val slice end ignores the test offset

- **Type:** slice-bounds
- **Symptom:** Test 2: g-03, g-05, g-06 and g-12 are missing from group_split. Test 3: val is empty and its label counts are all 0.
- **Location:** `splitkit/splitter.py` → `split_groups`
- **Why it fails:** The val slice must start after the test groups and run n_val further. Ending at n_val (equal to n_test here) gives an empty slice, so g-03, g-05, g-06 and g-12 get no split at all and their samples vanish.
- **Unblocks:** Test 2 every-group-assigned and the val split in Test 3.

Fix:

```diff
-        for gid in ordered[n_test:n_val]:
+        for gid in ordered[n_test:n_test + n_val]:
```

Observed with only this bug applied (`tests.test_2_splits.TestSplits.test_every_group_assigned`):

```
AssertionError: Lists differ: ['g-01', 'g-02', 'g-04', 'g-07', 'g-08', 'g-09', 'g-10', 'g-11[29 chars]-16'] != ['g-01', 'g-02', 'g-03', 'g-04', 'g-05', 'g-06', 'g-07', 'g-08[61 chars]-16']

First differing element 2:
'g-04'
'g-03'

Second list contains 4 additional elements.
First extra element 12:
'g-13'

  ['g-01',
   'g-02',
+  'g-03',
   'g-04',
+  'g-05',
+  'g-06',
   'g-07',
   'g-08',
   ' ...
```

### B6: All splits share one counts dict

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 3 only: label_counts reports the same totals for every split, e.g. train {'bird': 7, 'cat': 10, 'dog': 10} instead of {'bird': 4, 'cat': 4, 'dog': 4}.
- **Location:** `splitkit/reports.py` → `label_counts`
- **Why it fails:** Every split points at the same `empty` dict, so each sample increments one shared counter and every split reports the overall totals.
- **Unblocks:** Test 3 label_counts.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-    counts = {name: empty for name in SPLITS}
+    counts = {name: dict(empty) for name in SPLITS}
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_label_counts`):

```
AssertionError: {'train': {'bird': 7, 'cat': 10, 'dog': 10}, 'val': {'bird':[64 chars] 10}} != {'train': {'bird': 4, 'cat': 4, 'dog': 4}, 'val': {'bird': 2[58 chars]: 4}}
- {'test': {'bird': 7, 'cat': 10, 'dog': 10},
?                   ^         ^^         ^^

+ {'test': {'bird': 1, 'cat': 3, 'dog': 4},
?                   ^         ^         ^

-  'train': {'bird': 7, 'cat': 10, 'dog': 10},
?    ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `splitkit/splitter.py` → `apply_cap`: The `>=` check against the cap looks like it lets one too few through, but it runs before the increment, so exactly `cap` samples per label are kept. Sorting by (created_at, sample_id) is the spec's earliest-first order with id tie-break.
- `splitkit/utils.py` → `parse_timestamp`: It accepts exactly the four formats the README lists (two with time, two bare dates), with month/day order for the slash formats.
