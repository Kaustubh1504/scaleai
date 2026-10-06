# set-042 answer key: Teleop episode QA: sync, frame gaps and task metrics

**Domain:** robotics_episodes  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_validity.TestValidity.test_sync_ratios` | B1 Sync window excludes the 20 ms boundary |
| `test_1_validity.TestValidity.test_frame_rates` | B2 fps counts frames instead of intervals |
| `test_2_tasks.TestTaskMetrics.test_success_rates` | B3 Any non-blank success string counts as a success |
| `test_2_tasks.TestTaskMetrics.test_recorded_seconds` | B4 Recorded time floored to whole seconds |
| `test_3_report.TestSummary.test_tag_counts` | B5 Blank tags split into an empty tag |
| `test_3_report.TestSummary.test_operator_counts` | B6 Operator counts include rejected episodes |

## Failing pattern with all bugs present

- `tests.test_1_validity.TestValidity.test_frame_rates`
- `tests.test_1_validity.TestValidity.test_sync_ratios`
- `tests.test_2_tasks.TestTaskMetrics.test_recorded_seconds`
- `tests.test_2_tasks.TestTaskMetrics.test_success_rates`
- `tests.test_3_report.TestSummary.test_operator_counts`
- `tests.test_3_report.TestSummary.test_tag_counts`

## Bugs (recommended order)

### B1: Sync window excludes the 20 ms boundary

- **Type:** time-window-boundary
- **Symptom:** test_1 test_sync_ratios: EP-03 shows sync_ratio 0.95 instead of 1.0 (it still counts as valid). Every other ratio matches.
- **Location:** `robolog/sync.py` → `sync_ratio`
- **Why it fails:** Rule 4 makes the 20 ms window inclusive. With `<`, the three EP-03 camera frames whose nearest joint sample is exactly 20 ms away (around the joint dropouts at 400, 1200 and 2000 ms) count as unsynced.
- **Failing test:** `test_1_validity.TestValidity.test_sync_ratios`
- **Unblocks:** test_sync_ratios

Fix:

```diff
-nearest_offset(t, joints) < SYNC_TOLERANCE_MS
+nearest_offset(t, joints) <= SYNC_TOLERANCE_MS
```

Observed with only this bug applied (`tests.test_1_validity.TestValidity.test_sync_ratios`):

```
AssertionError: {'EP-03': 0.95, 'EP-04': None, 'EP-06': 0.66, 'EP-11': 0.9} != {'EP-04': None, 'EP-06': 0.66, 'EP-11': 0.9}
- {'EP-03': 0.95, 'EP-04': None, 'EP-06': 0.66, 'EP-11': 0.9}
?  ---------------

+ {'EP-04': None, 'EP-06': 0.66, 'EP-11': 0.9}
```

### B2: fps counts frames instead of intervals

- **Type:** off-by-one
- **Symptom:** test_1 test_frame_rates: every fps is a little too high (EP-01 25.42, EP-02 25.46, EP-05 23.58 ...) instead of 25.0 / 23.11 etc.
- **Location:** `robolog/validity.py` → `camera_stats`
- **Why it fails:** duration is measured first frame to last frame, which spans frames − 1 intervals. Dividing the frame count by it overstates the rate (60 frames over 2.36 s gives 25.42 instead of 25.0).
- **Failing test:** `test_1_validity.TestValidity.test_frame_rates`
- **Unblocks:** test_frame_rates

Fix:

```diff
-    fps = round(frames / (duration_ms / 1000), 2)
+    fps = round((frames - 1) / (duration_ms / 1000), 2)
```

Observed with only this bug applied (`tests.test_1_validity.TestValidity.test_frame_rates`):

```
AssertionError: {'EP-01': 25.42, 'EP-02': 25.46, 'EP-03': 25.42[203 chars]5.58} != {'EP-05': 23.11, 'EP-07': 30.3, 'EP-09': 20.0, [42 chars]3.33}
- {'EP-01': 25.42,
-  'EP-02': 25.46,
-  'EP-03': 25.42,
-  'EP-04': 25.51,
-  'EP-05': 23.58,
? ^            ^^

+ {'EP-05': 23.11,
? ^            ^^

-  'EP-06': 25.51,
-  'EP-07': 30.99,
?              ^^

+  'EP-07': 30.3,
?              ^

-  'EP-08 ...
```

### B3: Any non-blank success string counts as a success

- **Type:** bool-from-string
- **Symptom:** test_2 test_success_rates: pick 1.0 and pour 1.0 instead of 0.6 and 0.0; place and wipe unchanged.
- **Location:** `robolog/utils.py` → `parse_bool`
- **Why it fails:** bool() of any non-empty string is True, so `false`, `False` and `No` are read as successes. Only the blank EP-09 cell stays False.
- **Failing test:** `test_2_tasks.TestTaskMetrics.test_success_rates`
- **Unblocks:** test_success_rates

Fix:

```diff
-    return bool(clean(value))
+    return clean(value).lower() in TRUTHY
```

Observed with only this bug applied (`tests.test_2_tasks.TestTaskMetrics.test_success_rates`):

```
AssertionError: {'pick': 1.0, 'place': 1.0, 'pour': 1.0, 'wipe': 0.5} != {'pick': 0.6, 'place': 1.0, 'pour': 0.0, 'wipe': 0.5}
- {'pick': 1.0, 'place': 1.0, 'pour': 1.0, 'wipe': 0.5}
?          ^ ^                        ^

+ {'pick': 0.6, 'place': 1.0, 'pour': 0.0, 'wipe': 0.5}
?          ^ ^                        ^
```

### B4: Recorded time floored to whole seconds

- **Type:** integer-division
- **Symptom:** test_2 test_recorded_seconds: whole numbers {'pick': 11, 'place': 6, 'pour': 3, 'wipe': 3} instead of 11.07 / 6.12 / 3.5 / 3.94.
- **Location:** `robolog/metrics.py` → `task_metrics`
- **Why it fails:** `//` floors the millisecond total to whole seconds before rounding, so 11070 ms becomes 11 instead of 11.07. round() can't bring the lost fraction back.
- **Failing test:** `test_2_tasks.TestTaskMetrics.test_recorded_seconds`
- **Unblocks:** test_recorded_seconds

Fix:

```diff
-"recorded_s": round(recorded_ms // 1000, 2),
+"recorded_s": round(recorded_ms / 1000, 2),
```

Observed with only this bug applied (`tests.test_2_tasks.TestTaskMetrics.test_recorded_seconds`):

```
AssertionError: {'pick': 11, 'place': 6, 'pour': 3, 'wipe': 3} != {'pick': 11.07, 'place': 6.12, 'pour': 3.5, 'wipe': 3.94}
- {'pick': 11, 'place': 6, 'pour': 3, 'wipe': 3}
+ {'pick': 11.07, 'place': 6.12, 'pour': 3.5, 'wipe': 3.94}
?            +++            +++           ++           +++
```

### B5: Blank tags split into an empty tag

- **Type:** empty-split
- **Symptom:** test_3 test_tag_counts: tag_counts has an extra '' key with count 3 (and untagged would be empty).
- **Location:** `robolog/loader.py` → `split_tags`
- **Why it fails:** `"".split(";")` is `[""]`, not `[]`, so the three blank-tag episodes get one empty-string tag. tag_counts gains `"": 3` and untagged comes back empty.
- **Failing test:** `test_3_report.TestSummary.test_tag_counts`
- **Unblocks:** test_tag_counts

Fix:

```diff
-    return [tag.strip() for tag in text.split(";")]
+    return [tag.strip() for tag in text.split(";")] if text else []
```

Observed with only this bug applied (`tests.test_3_report.TestSummary.test_tag_counts`):

```
AssertionError: {'': 3, 'grasp': 3, 'pick': 3, 'place': 2, [41 chars]': 2} != {'grasp': 3, 'pick': 3, 'place': 2, 'pour':[34 chars]': 2}
- {'': 3,
-  'grasp': 3,
? ^

+ {'grasp': 3,
? ^

   'pick': 3,
   'place': 2,
   'pour': 1,
   'regrasp': 1,
   'slow': 1,
   'wipe': 2}
```

### B6: Operator counts include rejected episodes

- **Type:** counting-wrong-subset
- **Symptom:** test_3 test_operator_counts: {'alice': 5, 'bob': 4, 'carol': 3, 'dave': 4} instead of {'alice': 4, 'bob': 3, 'carol': 1, 'dave': 4}.
- **Location:** `robolog/report.py` → `summarize`
- **Why it fails:** The counter runs over every episode instead of the valid subset, so the four rejected episodes are credited to alice, bob and carol.
- **Failing test:** `test_3_report.TestSummary.test_operator_counts`
- **Unblocks:** test_operator_counts

Fix:

```diff
-    operators = Counter(ep.operator for ep in episodes)
+    operators = Counter(ep.operator for ep in valid)
```

Observed with only this bug applied (`tests.test_3_report.TestSummary.test_operator_counts`):

```
AssertionError: {'alice': 5, 'bob': 4, 'carol': 3, 'dave': 4} != {'alice': 4, 'bob': 3, 'carol': 1, 'dave': 4}
- {'alice': 5, 'bob': 4, 'carol': 3, 'dave': 4}
?           ^         ^           ^

+ {'alice': 4, 'bob': 3, 'carol': 1, 'dave': 4}
?           ^         ^           ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `robolog/sync.py` → `nearest_offset`: bisect_left returns the insertion point, so the closest sample is either just before it (i - 1) or at it (i). The bounds check handles t before the first or after the last sample, and `gap < best` is fine because equal gaps give the same distance either way.
