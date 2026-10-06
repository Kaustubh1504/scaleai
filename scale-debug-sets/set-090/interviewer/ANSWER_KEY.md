# set-090 answer key: Teleop episode QA with stream sync checks

**Domain:** robotics_episodes  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_validity.TestValidity.test_reasons`
- `tests.test_2_dataset.TestDataset.test_durations`
- `tests.test_2_dataset.TestDataset.test_task_table`
- `tests.test_3_report.TestReport.test_operators`
- `tests.test_3_report.TestReport.test_success_rate`
- `tests.test_3_report.TestReport.test_totals`

## Bugs (recommended order)

### B1: Episode robot ids not lower-cased

- **Type:** id-normalization
- **Symptom:** All three files fail. Test 1: E03 and E04 are unknown_robot. Test 2: their durations are None and open_drawer/pick_place lose them. Test 3: totals (6, 0.0056), open_drawer rate 1.0, pick_place 0.667, ana valid 1.
- **Location:** `episodeqa/loader.py` → `load_episodes`
- **Why it fails:** robots.json keys are lower-cased, but episode robot ids are only trimmed. E03 and E04 were logged as `R-02`, so the lookup fails and both are rejected as unknown_robot.
- **Unblocks:** E03/E04 in all three files. It also exposes B3.

Fix:

```diff
-            robot=clean(row["robot_id"]),
+            robot=norm(row["robot_id"]),
```

Observed with only this bug applied (`tests.test_1_validity.TestValidity.test_reasons`):

```
AssertionError: {'E01[24 chars]03': 'unknown_robot', 'E04': 'unknown_robot', [225 chars]ong'} != {'E01[24 chars]03': None, 'E04': None, 'E05': None, 'E06': No[203 chars]ong'}
  {'E01': None,
   'E02': None,
-  'E03': 'unknown_robot',
-  'E04': 'unknown_robot',
+  'E03': None,
+  'E04': None,
   'E05': None,
   'E06': None,
   'E07': None,
   'E08': 'dropped_frames',
   'E09': 'too_short',
   'E10' ...
```

### B2: Joint timestamps left in seconds

- **Type:** ms-vs-s
- **Symptom:** Test 1: E05 and E06 are out_of_sync. Test 2: the task table loses them (open_drawer total 2.0); durations are unchanged. Test 3: totals (6, 0.0053), open_drawer rate 0.0, ben valid 1 / dara valid 0.
- **Location:** `episodeqa/streams.py` → `prepare`
- **Why it fails:** Only the camera stream is converted to milliseconds. For r-03's episodes (unit sec / s), the camera is at ~1000-4000 ms and the joints stay at ~1.0-4.0, so no camera frame has a joint sample within 25 ms. ms episodes are unaffected because their scale is 1.
- **Unblocks:** E05/E06 back to valid in all three files.

Fix:

```diff
-    joints_ms = streams.get("joints", [])
+    joints_ms = to_ms(streams.get("joints", []), unit)
```

Observed with only this bug applied (`tests.test_1_validity.TestValidity.test_reasons`):

```
AssertionError: {'E01[50 chars]05': 'out_of_sync', 'E06': 'out_of_sync', 'E07[195 chars]ong'} != {'E01[50 chars]05': None, 'E06': None, 'E07': None, 'E08': 'd[177 chars]ong'}
  {'E01': None,
   'E02': None,
   'E03': None,
   'E04': None,
-  'E05': 'out_of_sync',
-  'E06': 'out_of_sync',
+  'E05': None,
+  'E06': None,
   'E07': None,
   'E08': 'dropped_frames',
   'E09': 'too_short',
   'E10': 'u ...
```

### B3: Joint stream shifted by the camera offset

- **Type:** wrong-field
- **Symptom:** Hidden while B1 is present (E03/E04 are already unknown_robot). Once B1 is fixed, E03 and E04 are out_of_sync instead of valid, with the same task-table and summary effects as B1 but with durations present.
- **Location:** `episodeqa/streams.py` → `prepare`
- **Why it fails:** r-02's joint clock runs 40 ms behind its camera (joint_offset_ms 40, camera_offset_ms 0). Using the camera offset for joints leaves every joint sample 35 ms away from its frame, so E03 and E04 are out_of_sync. This can't be seen while B1 rejects every r-02 episode as unknown_robot.
- **Unblocks:** E03/E04 valid in every file.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-t + robot.camera_offset_ms for t
+t + robot.joint_offset_ms for t
```

Observed with only this bug applied (`tests.test_1_validity.TestValidity.test_reasons`):

```
AssertionError: {'E01[24 chars]03': 'out_of_sync', 'E04': 'out_of_sync', 'E05[221 chars]ong'} != {'E01[24 chars]03': None, 'E04': None, 'E05': None, 'E06': No[203 chars]ong'}
  {'E01': None,
   'E02': None,
-  'E03': 'out_of_sync',
-  'E04': 'out_of_sync',
+  'E03': None,
+  'E04': None,
   'E05': None,
   'E06': None,
   'E07': None,
   'E08': 'dropped_frames',
   'E09': 'too_short',
   'E10': 'u ...
```

### B4: Camera period truncated

- **Type:** integer-division
- **Symptom:** Test 1: E07 is dropped_frames. Test 2: pick_place loses E07 (total 8.5). Test 3: totals (7, 0.0061), pick_place rate 1.0, chen valid 2 / 7.5 s.
- **Location:** `episodeqa/quality.py` → `gap_limit_ms`
- **Why it fails:** At 15 Hz the period is 66.67 ms, so the limit is 166.67 ms. Floor division gives 66, so the limit becomes 165, and E07's single 166 ms gap now counts as dropped frames. At 10 Hz the division is exact, so other robots are unaffected.
- **Unblocks:** E07 valid in all three files.

Fix:

```diff
-    return GAP_FACTOR * (1000 // robot.camera_hz)
+    return GAP_FACTOR * 1000 / robot.camera_hz
```

Observed with only this bug applied (`tests.test_1_validity.TestValidity.test_reasons`):

```
AssertionError: {'E01[76 chars]07': 'dropped_frames', 'E08': 'dropped_frames'[163 chars]ong'} != {'E01[76 chars]07': None, 'E08': 'dropped_frames', 'E09': 'to[151 chars]ong'}
  {'E01': None,
   'E02': None,
   'E03': None,
   'E04': None,
   'E05': None,
   'E06': None,
-  'E07': 'dropped_frames',
+  'E07': None,
   'E08': 'dropped_frames',
   'E09': 'too_short',
   'E10': 'uncalibrated',
   'E11' ...
```

### B5: Operator valid count includes failed checks

- **Type:** counting-wrong-subset
- **Symptom:** Only test_3 test_operators fails: ana shows valid 4 / valid_s 8.0 (expected 2 / 5.0). Every operator picks up their invalid episodes that have a duration.
- **Location:** `episodeqa/report.py` → `operator_table`
- **Why it fails:** Having a duration only means the episode got as far as the duration check. too_short, too_long, dropped_frames, out_of_sync and unlabelled episodes all have one, so they are counted as valid for their operator.
- **Unblocks:** test_operators.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-        if v.duration_s is not None:
+        if v.valid:
             row["valid"] += 1
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_operators`):

```
AssertionError: {'ana[24 chars]id': 4, 'valid_s': 8.0}, 'ben': {'submitted': [137 chars].87}} != {'ana[24 chars]id': 2, 'valid_s': 5.0}, 'ben': {'submitted': [135 chars]3.0}}
Diff is 724 characters long. Set self.maxDiff to None to see it.
```

### B6: 0.0 success rate reported as None

- **Type:** falsy-zero
- **Symptom:** Only test_3 test_success_rate fails: fold_towel and wipe_table are None instead of 0.0.
- **Location:** `episodeqa/report.py` → `success_rates`
- **Why it fails:** `x or None` replaces a real 0.0 with None, so tasks that have valid episodes but no successes (fold_towel, wipe_table) look as if there were no data. The spec says 0.0.
- **Unblocks:** test_success_rate.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-    return {task: round(wins[task] / n, 3) or None for task, n in sorted(totals.items())}
+    return {task: round(wins[task] / n, 3) for task, n in sorted(totals.items())}
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_success_rate`):

```
AssertionError: {'fold_towel': None, 'open_drawer': 0.5, 'pick_place': 0.75, 'wipe_table': None} != {'fold_towel': 0.0, 'open_drawer': 0.5, 'pick_place': 0.75, 'wipe_table': 0.0}
- {'fold_towel': None, 'open_drawer': 0.5, 'pick_place': 0.75, 'wipe_table': None}
?                ^^^^                                                        ^^^^

+ {'fold_towel': 0.0, 'open_drawer': 0.5, 'pick_place': ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `episodeqa/streams.py` → `drop_repeats`: It sorts first, so repeated timestamps end up next to each other, and then skips any value equal to the last one kept. Comparing with out[-1] is the standard way to dedupe a sorted sequence; E01's repeated frame is removed exactly once.
- `episodeqa/sync.py` → `nearest_gap`: bisect_left gives the insertion point i. The closest value is always at i-1 or i, and both are checked with bounds guards, so the edges of the stream and exact matches are handled. The loop over (i - 1, i) looks like an off-by-one, but it is correct.
