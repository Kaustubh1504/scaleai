# set-018 answer key: Teleop episode QA: frames, sync and validity

**Domain:** robotics_episodes  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_metrics.TestMetrics.test_1_frame_counts` | B1 Repeated camera timestamps counted as frames |
| `test_1_metrics.TestMetrics.test_2_durations` | B2 Duration floored to whole seconds |
| `test_1_metrics.TestMetrics.test_3_sync_rates` | B3 Sync tolerance made exclusive |
| `test_2_validity.TestValidity.test_4_inactive_robots` | B4 "no"/"false" robots treated as active |
| `test_2_validity.TestValidity.test_5_frame_gaps` | B5 Gap equal to the limit flagged |
| `test_3_summary.TestSummary.test_6_valid_minutes` | B6 Valid time divided as if it were seconds |

## Failing pattern with all bugs present

- `tests.test_1_metrics.TestMetrics.test_1_frame_counts`
- `tests.test_1_metrics.TestMetrics.test_2_durations`
- `tests.test_1_metrics.TestMetrics.test_3_sync_rates`
- `tests.test_2_validity.TestValidity.test_4_inactive_robots`
- `tests.test_2_validity.TestValidity.test_5_frame_gaps`
- `tests.test_3_summary.TestSummary.test_6_valid_minutes`

## Bugs (recommended order)

### B1: Repeated camera timestamps counted as frames

- **Type:** missing-dedupe
- **Symptom:** test_1_frame_counts fails: EP01 shows 32 frames instead of 30 and EP07 32 instead of 31. Gaps, durations and sync rates are unchanged.
- **Location:** `teleop/metrics.py` → `frame_times`
- **Why it fails:** The camera log repeats some timestamps, and the spec counts one frame per distinct timestamp. Sorting without set() keeps the repeats. They add 0 ms gaps and are always matched, so only the frame count changes.
- **Failing test:** `test_1_metrics.TestMetrics.test_1_frame_counts`
- **Unblocks:** test_1_frame_counts.

Fix:

```diff
-    return sorted(raw)
+    return sorted(set(raw))
```

Observed with only this bug applied (`tests.test_1_metrics.TestMetrics.test_1_frame_counts`):

```
AssertionError: {'EP01': 32, 'EP02': 41, 'EP03': 25, 'EP04': 18, 'E[88 chars]: 28} != {'EP01': 30, 'EP02': 41, 'EP03': 25, 'EP04': 18, 'E[88 chars]: 28}
- {'EP01': 32,
?           ^

+ {'EP01': 30,
?           ^

   'EP02': 41,
   'EP03': 25,
   'EP04': 18,
   'EP05': 15,
   'EP06': 35,
-  'EP07': 32,
?           ^

+  'EP07': 31,
?           ^

   'EP08': 30,
   'EP09': 40,
   'EP10': 51,
   'EP1 ...
```

### B2: Duration floored to whole seconds

- **Type:** integer-division
- **Symptom:** test_2_durations fails: every duration is a whole number (EP01 2 instead of 2.9, EP03 2 instead of 2.44, EP08 3 instead of 3.06, EP09 3 instead of 3.9 ...). Validity is unchanged.
- **Location:** `teleop/metrics.py` → `compute_metrics`
- **Why it fails:** `//` floors the millisecond span to whole seconds before round() runs, so 2.9 s becomes 2. It never changes the too_short check, because floor(x) >= 2 exactly when x >= 2.
- **Failing test:** `test_1_metrics.TestMetrics.test_2_durations`
- **Unblocks:** test_2_durations.

Fix:

```diff
-        duration_s=round(span_ms // 1000, 2),
+        duration_s=round(span_ms / 1000, 2),
```

Observed with only this bug applied (`tests.test_1_metrics.TestMetrics.test_2_durations`):

```
AssertionError: {'EP01': 2, 'EP02': 4, 'EP03': 2, 'EP04': 1, 'EP05'[76 chars]': 2} != {'EP01': 2.9, 'EP02': 4.0, 'EP03': 2.44, 'EP04': 1.[104 chars]2.67}
- {'EP01': 2,
+ {'EP01': 2.9,
?           ++

-  'EP02': 4,
+  'EP02': 4.0,
?           ++

-  'EP03': 2,
+  'EP03': 2.44,
?           +++

-  'EP04': 1,
+  'EP04': 1.7,
?           ++

-  'EP05': 1,
+  'EP05': 1.4,
?           ++

-  'EP06': 3,
 ...
```

### B3: Sync tolerance made exclusive

- **Type:** time-window-boundary
- **Symptom:** test_3_sync_rates fails: EP02 drops to 0.951 and EP10 to 0.941 instead of 1.0. Neither falls below 0.9, so validity is unchanged.
- **Location:** `teleop/metrics.py` → `sync_rate`
- **Why it fails:** The spec says a joint sample exactly sync_tolerance_ms away still counts. With `<`, frames exactly 10 ms from their nearest joint sample stop matching.
- **Failing test:** `test_1_metrics.TestMetrics.test_3_sync_rates`
- **Unblocks:** test_3_sync_rates.

Fix:

```diff
-        if gap is not None and gap < tolerance_ms:
+        if gap is not None and gap <= tolerance_ms:
```

Observed with only this bug applied (`tests.test_1_metrics.TestMetrics.test_3_sync_rates`):

```
AssertionError: {'EP01': 1.0, 'EP02': 0.951, 'EP03': 1.0, 'EP04': 1.0, 'EP05': [94 chars] 1.0} != {'EP01': 1.0, 'EP02': 1.0, 'EP03': 1.0, 'EP04': 1.0, 'EP05': 1.[90 chars] 1.0}
  {'EP01': 1.0,
-  'EP02': 0.951,
?           ----

+  'EP02': 1.0,
?          ++

   'EP03': 1.0,
   'EP04': 1.0,
   'EP05': 1.0,
   'EP06': 0.771,
   'EP07': 1.0,
   'EP08': 1.0,
   'EP09': 0.5,
-  'EP10': 0.941,
?        ...
```

### B4: "no"/"false" robots treated as active

- **Type:** bool-from-string
- **Symptom:** test_4_inactive_robots fails: no episode is flagged robot_inactive ([] instead of ['EP05', 'EP09']). The valid set is unchanged because both episodes break other rules.
- **Location:** `teleop/loader.py` → `parse_bool`
- **Why it fails:** bool() of a non-empty string is always True, so RB-04 (`no`) and RB-07 (`false`) load as active and their episodes lose the robot_inactive reason. Both episodes are invalid for other reasons too, so the valid set doesn't change.
- **Failing test:** `test_2_validity.TestValidity.test_4_inactive_robots`
- **Unblocks:** test_4_inactive_robots.

Fix:

```diff
-    return bool(text)
+    return text.lower() in TRUTHY
```

Observed with only this bug applied (`tests.test_2_validity.TestValidity.test_4_inactive_robots`):

```
AssertionError: Lists differ: [] != ['EP05', 'EP09']

Second list contains 2 additional elements.
First extra element 0:
'EP05'

- []
+ ['EP05', 'EP09']
```

### B5: Gap equal to the limit flagged

- **Type:** off-by-one
- **Symptom:** test_5_frame_gaps fails: frame_gap is ['EP06', 'EP08'] instead of ['EP08']. EP06 is already unsynced, so the valid set is unchanged.
- **Location:** `teleop/validity.py` → `check_episode`
- **Why it fails:** The spec flags a gap only when it is greater than the robot's limit. `>=` also flags EP06, whose largest gap is exactly 150 ms on a robot whose limit is 150 ms.
- **Failing test:** `test_2_validity.TestValidity.test_5_frame_gaps`
- **Unblocks:** test_5_frame_gaps.

Fix:

```diff
-    if robot is not None and metrics.max_gap_ms >= robot.max_gap_ms:
+    if robot is not None and metrics.max_gap_ms > robot.max_gap_ms:
```

Observed with only this bug applied (`tests.test_2_validity.TestValidity.test_5_frame_gaps`):

```
AssertionError: Lists differ: ['EP06', 'EP08'] != ['EP08']

First differing element 0:
'EP06'
'EP08'

First list contains 1 additional elements.
First extra element 1:
'EP08'

- ['EP06', 'EP08']
+ ['EP08']
```

### B6: Valid time divided as if it were seconds

- **Type:** ms-vs-s
- **Symptom:** test_6_valid_minutes fails: valid_minutes is 366.83 instead of 0.37.
- **Location:** `teleop/reports.py` → `summarize`
- **Why it fails:** The spans are in milliseconds. Dividing by 60 treats them as seconds, so the total is 1000 times too large.
- **Failing test:** `test_3_summary.TestSummary.test_6_valid_minutes`
- **Unblocks:** test_6_valid_minutes.

Fix:

```diff
-    return {"by_task": tasks, "valid_minutes": round(valid_ms / 60, 2)}
+    return {"by_task": tasks, "valid_minutes": round(valid_ms / 60_000, 2)}
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_6_valid_minutes`):

```
AssertionError: 366.83 != 0.37
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `teleop/metrics.py` → `nearest_gap`: The slice `sorted_ts[max(i - 1, 0):i + 1]` looks like it could miss a neighbour or go out of range, but bisect_left puts t between index i-1 and i, so those are the only two candidates, the slice clamps at both ends, and an empty list returns None.
