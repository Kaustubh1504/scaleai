# set-061 answer key: Rushing and copying tripwire

**Domain:** fraud_detection  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_signals.TestSignals.test_1_rush_rates` | B1 Rush rate floored by integer division |
| `test_1_signals.TestSignals.test_2_shared_answer_counts` | B2 Own submission ends the twin search |
| `test_2_report.TestReport.test_3_worst_rusher` | B3 Worst-rusher tie goes to first seen |

## Failing pattern with all bugs present

- `tests.test_1_signals.TestSignals.test_1_rush_rates`
- `tests.test_1_signals.TestSignals.test_2_shared_answer_counts`
- `tests.test_2_report.TestReport.test_3_worst_rusher`

## Bugs (recommended order)

### B1: Rush rate floored by integer division

- **Type:** integer-division
- **Symptom:** Test 1 test_1_rush_rates: A02 shows 33 instead of 33.3, and every rate comes back as a whole number (0, 50) rather than a float. Flags and worst_rusher are unchanged.
- **Location:** `tripwire/timing.py` → `rush_stats`
- **Why it fails:** `100 * rushed // timed` floors to a whole percentage before round() runs, so 1 of 3 becomes 33 instead of 33.3. Rates that divide evenly (0, 50) look fine, which hides it.
- **Failing test:** `test_1_signals.TestSignals.test_1_rush_rates`
- **Unblocks:** test_1_rush_rates.

Fix:

```diff
-row["rush_rate"] = round(100 * row["rushed"] // row["timed"], 1)
+row["rush_rate"] = round(100 * row["rushed"] / row["timed"], 1)
```

Observed with only this bug applied (`tests.test_1_signals.TestSignals.test_1_rush_rates`):

```
AssertionError: {'A01': 0, 'A02': 33, 'A03': 50, 'A04': 0, 'A05': [28 chars]': 0} != {'A01': 0.0, 'A02': 33.3, 'A03': 50.0, 'A04': 0.0,[44 chars] 0.0}
- {'A01': 0,
+ {'A01': 0.0,
?         ++

-  'A02': 33,
+  'A02': 33.3,
?           ++

-  'A03': 50,
+  'A03': 50.0,
?           ++

-  'A04': 0,
+  'A04': 0.0,
?         ++

-  'A05': 50,
+  'A05': 50.0,
?           ++

-  'A06': 0,
+  'A06': 0.0, ...
```

### B2: Own submission ends the twin search

- **Type:** early-return
- **Symptom:** Test 1 test_2_shared_answer_counts: A04 and A08 get 2 shared answers each instead of 4, and A01 drops out (0 instead of 1). The copying flags stay the same, so Test 2 still passes.
- **Location:** `tripwire/duplicates.py` → `has_twin`
- **Why it fails:** The task's submission list includes the submission itself. Returning False when the loop reaches the annotator's own row stops the search, so whoever answered first on a task never sees the later identical answer.
- **Failing test:** `test_1_signals.TestSignals.test_2_shared_answer_counts`
- **Unblocks:** test_2_shared_answer_counts.

Fix:

```diff
         if other.annotator_id == sub.annotator_id:
-            return False
+            continue
```

Observed with only this bug applied (`tests.test_1_signals.TestSignals.test_2_shared_answer_counts`):

```
AssertionError: {'A02': 1, 'A04': 2, 'A08': 2} != {'A01': 1, 'A02': 1, 'A04': 4, 'A08': 4}
- {'A02': 1, 'A04': 2, 'A08': 2}
?                   ^         ^

+ {'A01': 1, 'A02': 1, 'A04': 4, 'A08': 4}
?  ++++++++++                 ^         ^
```

### B3: Worst-rusher tie goes to first seen

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_3_worst_rusher: returns A05 instead of A03. Both have rush_rate 50.0.
- **Location:** `tripwire/report.py` → `worst_rusher`
- **Why it fails:** max() returns the first annotator to reach the top rate, and `rush` is ordered by first submission in the file, not by id. A05 submits before A03, so the 50.0 tie goes to A05 instead of the lowest id.
- **Failing test:** `test_2_report.TestReport.test_3_worst_rusher`
- **Unblocks:** test_3_worst_rusher.

Fix:

```diff
-    return max(timed, key=lambda a: timed[a]["rush_rate"])
+    return min(timed, key=lambda a: (-timed[a]["rush_rate"], a))
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_3_worst_rusher`):

```
AssertionError: 'A05' != 'A03'
- A05
?   ^
+ A03
?   ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `tripwire/timing.py` → `median`: The `//` only computes the middle index, which must be an integer. The even case divides the sum of the two middle values with `/`, so t2 correctly gives 112.5. It looks like the integer-division suspect but it is fine.
