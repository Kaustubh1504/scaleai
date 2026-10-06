# set-013 answer key: Annotator speeding and copy detection

**Domain:** fraud_detection  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_annotators.TestAnnotators.test_annotator_table`
- `tests.test_2_summary.TestSummary.test_copy_tasks`
- `tests.test_2_summary.TestSummary.test_flagged_annotators`
- `tests.test_2_summary.TestSummary.test_rejected_submissions`

## Bugs (recommended order)

### B1: Submission annotator ids not lower-cased

- **Type:** id-normalization
- **Symptom:** Test 1 test_annotator_table: ann-04 shows 3 submissions, fast_ratio 0.333 and no flags (expected 4 / 0.5 / speeding). Test 2: ann-04 is missing from flagged, and rejected is [] instead of ['s13'].
- **Location:** `fraudscan/loader.py` → `load_submissions`
- **Why it fails:** The registry keys are lower-cased but submission ids are only trimmed, so rows written as 'ANN-04' / ' Ann-04' fail the registry check and are skipped as unknown annotators.
- **Unblocks:** Test 1 row for ann-04 and the ann-04 entry in Test 2's flagged list. Exposes B2.

Fix:

```diff
-            annotator_id = row["annotator_id"].strip()
+            annotator_id = norm_annotator(row["annotator_id"])
```

Observed with only this bug applied (`tests.test_1_annotators.TestAnnotators.test_annotator_table`):

```
AssertionError: {'ann[223 chars]ns': 3, 'fast_ratio': 0.333, 'flags': []}, 'an[391 chars] []}} != {'ann[223 chars]ns': 4, 'fast_ratio': 0.5, 'flags': ['speeding[399 chars] []}}
  {'ann-01': {'fast_ratio': 0.0, 'flags': [], 'submissions': 3},
   'ann-02': {'fast_ratio': 0.75, 'flags': ['speeding'], 'submissions': 4},
   'ann-03': {'fast_ratio': 0.0, 'flags': ['copying'], 'submissions': 2},
-  'ann- ...
```

### B2: Rejected submissions silently dropped

- **Type:** swallowed-exception
- **Symptom:** Only visible after B1 is fixed. Test 2 test_rejected_submissions: rejected is [] instead of ['s13']. Test 1 passes.
- **Location:** `fraudscan/loader.py` → `load_submissions`
- **Why it fails:** The handler catches the parse error and moves on without recording the row, so a rejected submission disappears instead of being reported. The only such row (s13) belongs to ann-04 and is written ' Ann-04', so while B1 drops it as unknown the output is the same with or without this bug.
- **Unblocks:** Test 2 rejected list.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
             except ValueError:
+                rejected.append(row["submission_id"].strip())
                 continue
```

Observed with only this bug applied (`tests.test_2_summary.TestSummary.test_rejected_submissions`):

```
AssertionError: Lists differ: [] != ['s13']

Second list contains 1 additional elements.
First extra element 0:
's13'

- []
+ ['s13']
```

### B3: Same annotator resubmitting counted as copying

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_annotator_table: ann-06 is flagged ['copying']. Test 2: copy_tasks gains 'T4': ['ann-06'] and ann-06 appears in flagged.
- **Location:** `fraudscan/copying.py` → `copy_tasks`
- **Why it fails:** A list keeps one entry per submission, so ann-06 submitting the same answer twice on T4 makes len(who) == 2 although only one annotator is involved. The spec needs two different annotators.
- **Unblocks:** Test 1 row for ann-06 and the Test 2 flagged / copy_tasks entries.

Fix:

```diff
-        who = [s.annotator_id for s in group]
+        who = {s.annotator_id for s in group}
```

Observed with only this bug applied (`tests.test_1_annotators.TestAnnotators.test_annotator_table`):

```
AssertionError: {'ann[398 chars]s': ['copying']}, 'ann-07': {'submissions': 2,[233 chars] []}} != {'ann[398 chars]s': []}, 'ann-07': {'submissions': 2, 'fast_ra[224 chars] []}}
  {'ann-01': {'fast_ratio': 0.0, 'flags': [], 'submissions': 3},
   'ann-02': {'fast_ratio': 0.75, 'flags': ['speeding'], 'submissions': 4},
   'ann-03': {'fast_ratio': 0.0, 'flags': ['copying'], 'submissions': 2},
   'ann- ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `fraudscan/timing.py` → `is_fast`: `<` looks like a boundary slip, but the spec says under 20 seconds is fast and exactly 20 is not. ann-07's 20-second submission confirms it. The duration uses total_seconds(), not .seconds.
- `fraudscan/copying.py` → `norm_answer`: split()/join collapses every run of whitespace and trims the ends, lower() handles case, and rstrip('.!?') drops trailing punctuation, exactly as README rule 4 says.
