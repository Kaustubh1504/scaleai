# set-018 interviewer notes

**Scenario:** Measure each teleoperation episode (distinct camera frames, duration, frame gaps, camera-to-joint sync), apply validity rules per robot, and summarise valid episodes per task. Test 3 reports usable minutes.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Repeated camera timestamps counted as frames

1. **Nudge:** Only EP01 and EP07 have too many frames. Look at their camera_ms lists in frames.json.
2. **Area:** Look at how the raw camera timestamps become frames.
3. **Exact:** frame_times should be sorted(set(raw)).

### B2: Duration floored to whole seconds

1. **Nudge:** Every duration is a whole number. Is that plausible?
2. **Area:** Look at how span_ms is turned into seconds.
3. **Exact:** Use / 1000, not // 1000.

### B3: Sync tolerance made exclusive

1. **Nudge:** EP02 and EP10 lose a few matches. How far are their unmatched frames from the nearest joint sample?
2. **Area:** Check the tolerance comparison in sync_rate against metrics rule 5.
3. **Exact:** Use gap <= tolerance_ms.

### B4: "no"/"false" robots treated as active

1. **Nudge:** No episode is flagged robot_inactive. Which robots are inactive in robots.csv?
2. **Area:** Look at how the `active` column is parsed.
3. **Exact:** parse_bool should return text.lower() in TRUTHY.

### B5: Gap equal to the limit flagged

1. **Nudge:** EP06 is flagged frame_gap. Compare its max_gap_ms with its robot's limit.
2. **Area:** Look at the frame_gap rule in validity.py.
3. **Exact:** Use > robot.max_gap_ms.

### B6: Valid time divided as if it were seconds

1. **Nudge:** Seven episodes of 2–5 seconds can't add up to 366 minutes.
2. **Area:** Check the units of span_ms in the valid_minutes calculation.
3. **Exact:** Divide by 60_000.

## "Why did that fix work?" probes

**B1**
- Why didn't the extra frames change max_gap_ms or duration_s?
- Under what data would the repeats have changed sync_rate as well?

**B2**
- Why didn't the validity tests notice whole-second durations?
- If min_duration_s were 2.5, what would this have done to EP01?

**B3**
- Why didn't EP02 or EP10 become unsynced?
- How would you test the boundary so this fails loudly?

**B4**
- Why does a blank `active` cell still come out active with the original code?
- Why did test_valid_episodes keep passing?

**B5**
- Why didn't EP03 (140 ms gap) get flagged?
- Why is EP06 invalid either way?

**B6**
- Why does the spec say to use the raw spans and not the rounded duration_s values?
- How would you name variables so that a unit slip like this is harder to make?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `teleop/metrics.py` → `nearest_gap`: The slice `sorted_ts[max(i - 1, 0):i + 1]` looks like it could miss a neighbour or go out of range, but bisect_left puts t between index i-1 and i, so those are the only two candidates, the slice clamps at both ends, and an empty list returns None.
