# set-066 interviewer notes

**Scenario:** Validate robot-arm teleop episodes (robot in service, both streams present, enough frames, no camera gaps, camera/joint sync within 20 ms) and summarise the accepted ones. The frame-gap unit slip rejects nearly everything and hides the sync-boundary slip.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Re-sent camera frames counted twice

1. **Nudge:** EP-09 has one frame more than expected. Look at its raw timestamps in streams.json.
2. **Area:** Look at how load_streams turns the raw list into timestamps_ms.
3. **Exact:** sorted(to_ms(t, unit) for t in ...) keeps duplicates; use a set comprehension: sorted({to_ms(t, unit) for t in rec['t']}).

### B2: Episode robot ids not lower-cased

1. **Nudge:** EP-03 and EP-13 are rejected as robot_unavailable. Are their robots in robots.json?
2. **Area:** Compare how robot ids are normalised in load_robots and load_episodes.
3. **Exact:** load_episodes uses clean(row['robot_id']); it should use norm_robot().

### B3: Frame period computed in seconds

1. **Nudge:** Every episode that has enough frames is rejected as frame_gap, even ones with perfectly regular 100 ms frames.
2. **Area:** Look at how the allowed gap is derived from rate_hz.
3. **Exact:** period_ms = 1 / rate_hz is seconds; use 1000 / robot.rate_hz.

### B4: Sync tolerance made exclusive

1. **Nudge:** EP-07 is rejected as desync. Work out the offset of each camera frame to its nearest joint sample.
2. **Area:** Two frames are exactly 20 ms off. Check the comparison in sync_ratio against the README.
3. **Exact:** Use nearest_offset(joints, t) <= SYNC_TOLERANCE_MS.

### B5: Exactly 6 frames treated as too short

1. **Nudge:** EP-05 is rejected as too_short. How many frames does it have?
2. **Area:** Compare the too_short check with README check 3.
3. **Exact:** Use stats['frames'] < MIN_FRAMES.

### B6: Reason counter updated with a string

1. **Nudge:** invalid_reasons has single-letter keys. Where could letters come from?
2. **Area:** Look at how summarize adds each invalid episode's reason to the Counter.
3. **Exact:** reasons.update(r.reason) counts characters; use reasons[r.reason] += 1.

## "Why did that fix work?" probes

**B1**
- Why didn't the duplicate frame change EP-09's max_gap_ms or validity?
- Joint streams go through the same code. What would a duplicate joint sample do to the sync ratio?

**B2**
- Why did EP-14 (' arm-10') survive even though its id also needed cleaning?
- Why is it safer to normalise ids in one helper used by both loaders?

**B3**
- Why were EP-04, EP-06, EP-10 and EP-12 unaffected?
- Why did the sync-tolerance problem only show up after this fix?

**B4**
- Why was this invisible while the frame period was in seconds?
- nearest_offset is marked VERIFIED. How did you confirm the problem wasn't there?

**B5**
- Which other episode sits near this boundary, and why is it still correctly rejected?
- What single data row would you add to guard this boundary in tests?

**B6**
- What would reasons.update([r.reason]) have done?
- Why did Tests 1 and 2 never notice this?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `episodekit/sync.py` → `nearest_offset`: bisect_left gives the insertion point, so the nearest sample is either just before or just at it; the slice [i-1:i+1] (clamped at 0) holds exactly those neighbours and also handles t before the first or after the last sample.
- `episodekit/streams.py` → `to_ms`: round(value * 1000) looks like it could drift on floats such as 12.1, but rounding to the nearest integer absorbs the 1e-12 error, which is exactly the 'convert, then round' rule in the README. Callers already lower-case and trim the unit.
