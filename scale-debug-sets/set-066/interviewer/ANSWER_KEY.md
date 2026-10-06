# set-066 answer key: Teleop episode QA: units, sync tolerance, frame gaps

**Domain:** robotics_episodes  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_streams.TestStreams.test_camera_stats`
- `tests.test_2_validity.TestValidity.test_rejection_reasons`
- `tests.test_2_validity.TestValidity.test_valid_episodes`
- `tests.test_3_report.TestReport.test_invalid_reasons`
- `tests.test_3_report.TestReport.test_sync_and_duration`
- `tests.test_3_report.TestReport.test_totals`
- `tests.test_3_report.TestReport.test_valid_by_day`
- `tests.test_3_report.TestReport.test_valid_by_task`

## Bugs (recommended order)

### B1: Re-sent camera frames counted twice

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_camera_stats: EP-09 shows frames 8 instead of 7 (duration and max gap unchanged). Nothing else fails.
- **Location:** `episodekit/streams.py` → `load_streams`
- **Why it fails:** A generator instead of a set comprehension keeps duplicate timestamps, so the re-sent 3100 ms frame in EP-09 is counted as a second frame (README: a repeated timestamp counts once).
- **Unblocks:** Test 1 camera stats.

Fix:

```diff
-        stamps = sorted(to_ms(t, unit) for t in rec["t"])
+        stamps = sorted({to_ms(t, unit) for t in rec["t"]})
```

Observed with only this bug applied (`tests.test_1_streams.TestStreams.test_camera_stats`):

```
AssertionError: {'EP-[515 chars]es': 8, 'duration_ms': 350, 'max_gap_ms': 100}[246 chars] 40}} != {'EP-[515 chars]es': 7, 'duration_ms': 350, 'max_gap_ms': 100}[246 chars] 40}}
  {'EP-01': {'duration_ms': 700, 'frames': 8, 'max_gap_ms': 100},
   'EP-02': {'duration_ms': 700, 'frames': 8, 'max_gap_ms': 100},
   'EP-03': {'duration_ms': 450, 'frames': 10, 'max_gap_ms': 50},
   'EP-04': {'duration_ms ...
```

### B2: Episode robot ids not lower-cased

- **Type:** id-normalization
- **Symptom:** Test 2: EP-03 and EP-13 are rejected as robot_unavailable, so valid shrinks to 6 episodes. Test 3: robot_unavailable 4, valid 6, pick/place 2 each, mean_sync_ratio 0.955, valid_duration_s 3.2.
- **Location:** `episodekit/loader.py` → `load_episodes`
- **Why it fails:** The registry keys are lower-cased by norm_robot, but episode robot ids are only trimmed, so 'ARM-03' and 'ARM-09' miss the lookup and the episodes look like they were recorded on unknown robots.
- **Unblocks:** Test 2 for EP-03 and EP-13.

Fix:

```diff
-                robot_id=clean(row["robot_id"]),
+                robot_id=norm_robot(row["robot_id"]),
```

Observed with only this bug applied (`tests.test_2_validity.TestValidity.test_rejection_reasons`):

```
AssertionError: {'EP-03': 'robot_unavailable', 'EP-04': 'robot_[158 chars]ble'} != {'EP-04': 'robot_unavailable', 'EP-06': 'too_sh[98 chars]ble'}
- {'EP-03': 'robot_unavailable',
?       ^

+ {'EP-04': 'robot_unavailable',
?       ^

-  'EP-04': 'robot_unavailable',
   'EP-06': 'too_short',
   'EP-08': 'frame_gap',
   'EP-10': 'missing_stream',
   'EP-11': 'desync',
-  'EP-12': 'robot_unavailable' ...
```

### B3: Frame period computed in seconds

- **Type:** ms-vs-s
- **Symptom:** Test 2: no episode is valid; every episode that reaches the gap check (10 of them) is rejected as frame_gap. Test 3: valid 0, empty task/day counts, invalid_reasons frame_gap 10, mean_sync_ratio None, valid_duration_s 0.0.
- **Location:** `episodekit/validity.py` → `max_gap_allowed`
- **Why it fails:** 1 / rate_hz is the period in seconds (0.1 for 10 Hz), but camera gaps are in milliseconds, so the allowed gap becomes 0.2 ms and every episode that reaches the gap check is rejected as frame_gap.
- **Unblocks:** Most of Test 2 and Test 3, and it exposes B4.

Fix:

```diff
-    period_ms = 1 / robot.rate_hz
+    period_ms = 1000 / robot.rate_hz
```

Observed with only this bug applied (`tests.test_2_validity.TestValidity.test_rejection_reasons`):

```
AssertionError: {'EP-01': 'frame_gap', 'EP-02': 'frame_gap', 'E[277 chars]gap'} != {'EP-04': 'robot_unavailable', 'EP-06': 'too_sh[98 chars]ble'}
- {'EP-01': 'frame_gap',
-  'EP-02': 'frame_gap',
-  'EP-03': 'frame_gap',
-  'EP-04': 'robot_unavailable',
? ^

+ {'EP-04': 'robot_unavailable',
? ^

-  'EP-05': 'frame_gap',
   'EP-06': 'too_short',
-  'EP-07': 'frame_gap',
   'EP-08': 'frame_gap',
-   ...
```

### B4: Sync tolerance made exclusive

- **Type:** time-window-boundary
- **Symptom:** Only visible after B3 is fixed. Test 2: EP-07 is rejected as desync. Test 3: valid 7, desync 2, pick 2, 2026-04-03 count 2, (mean_sync_ratio, valid_duration_s) = (0.962, 3.7).
- **Location:** `episodekit/sync.py` → `sync_ratio`
- **Why it fails:** The README counts a joint sample exactly 20 ms away as synced. With `<`, EP-07's two 20 ms frames are unsynced, its ratio drops to 0.75 and it is rejected as desync.
- **Unblocks:** Test 2 (EP-07) and the Test 3 counts.
- **Masked:** invisible until B3 is fixed (identical test output either way).

Fix:

```diff
-    synced = sum(1 for t in camera if nearest_offset(joints, t) < SYNC_TOLERANCE_MS)
+    synced = sum(1 for t in camera if nearest_offset(joints, t) <= SYNC_TOLERANCE_MS)
```

Observed with only this bug applied (`tests.test_2_validity.TestValidity.test_rejection_reasons`):

```
AssertionError: {'EP-[48 chars]'EP-07': 'desync', 'EP-08': 'frame_gap', 'EP-1[65 chars]ble'} != {'EP-[48 chars]'EP-08': 'frame_gap', 'EP-10': 'missing_stream[46 chars]ble'}
  {'EP-04': 'robot_unavailable',
   'EP-06': 'too_short',
-  'EP-07': 'desync',
   'EP-08': 'frame_gap',
   'EP-10': 'missing_stream',
   'EP-11': 'desync',
   'EP-12': 'robot_unavailable'}
```

### B5: Exactly 6 frames treated as too short

- **Type:** off-by-one
- **Symptom:** Test 2: EP-05 (exactly 6 frames) is rejected as too_short. Test 3: valid 7, too_short 2, stack 1, 2026-04-03 count 2, (0.962, 3.9).
- **Location:** `episodekit/validity.py` → `check_episode`
- **Why it fails:** The spec rejects fewer than 6 frames; `<=` also rejects EP-05, which has exactly 6.
- **Unblocks:** Test 2 (EP-05) and Test 3 stack/day counts.

Fix:

```diff
-    if stats["frames"] <= MIN_FRAMES:
+    if stats["frames"] < MIN_FRAMES:
```

Observed with only this bug applied (`tests.test_2_validity.TestValidity.test_rejection_reasons`):

```
AssertionError: {'EP-[26 chars]'EP-05': 'too_short', 'EP-06': 'too_short', 'E[90 chars]ble'} != {'EP-[26 chars]'EP-06': 'too_short', 'EP-08': 'frame_gap', 'E[68 chars]ble'}
  {'EP-04': 'robot_unavailable',
-  'EP-05': 'too_short',
   'EP-06': 'too_short',
   'EP-08': 'frame_gap',
   'EP-10': 'missing_stream',
   'EP-11': 'desync',
   'EP-12': 'robot_unavailable'}
```

### B6: Reason counter updated with a string

- **Type:** counter-misuse
- **Symptom:** Test 3 test_invalid_reasons only: the dict has single-letter keys ('_': 5, 'a': 9, 'b': 4, ...) instead of reason names.
- **Location:** `episodekit/reports.py` → `summarize`
- **Why it fails:** Counter.update() iterates its argument, so a reason string is counted letter by letter instead of as one key.
- **Unblocks:** Test 3 invalid_reasons.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-            reasons.update(r.reason)
+            reasons[r.reason] += 1
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_invalid_reasons`):

```
AssertionError: {'_': 5, 'a': 9, 'b': 4, 'c': 1, 'd': 1, 'e[120 chars]': 1} != {'desync': 1, 'frame_gap': 1, 'missing_stre[42 chars]': 1}
+ {'desync': 1,
+  'frame_gap': 1,
+  'missing_stream': 1,
+  'robot_unavailable': 2,
+  'too_short': 1}
- {'_': 5,
-  'a': 9,
-  'b': 4,
-  'c': 1,
-  'd': 1,
-  'e': 5,
-  'f': 1,
-  'g': 2,
-  'h': 1,
-  'i': 4,
-  'l': 4,
-  'm': 3,
-  'n': 4,
-  'o': 7,
-   ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `episodekit/sync.py` → `nearest_offset`: bisect_left gives the insertion point, so the nearest sample is either just before or just at it; the slice [i-1:i+1] (clamped at 0) holds exactly those neighbours and also handles t before the first or after the last sample.
- `episodekit/streams.py` → `to_ms`: round(value * 1000) looks like it could drift on floats such as 12.1, but rounding to the nearest integer absorbs the 1e-12 error, which is exactly the 'convert, then round' rule in the README. Callers already lower-case and trim the unit.
