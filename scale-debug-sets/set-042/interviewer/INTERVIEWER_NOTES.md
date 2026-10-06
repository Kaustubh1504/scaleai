# set-042 interviewer notes

**Scenario:** Validate robot teleop episodes (missing streams, too few frames, camera frame gaps, camera/joint sync within an inclusive 20 ms window), then report per-task success and recorded time and fleet-level tag/operator counts.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Sync window excludes the 20 ms boundary

1. **Nudge:** EP-03 is reported at 0.95. Look at its joint stream around 400 ms: which sample is nearest to that camera frame?
2. **Area:** Check how sync_ratio decides that a frame is synced against README rule 4.
3. **Exact:** Use `<= SYNC_TOLERANCE_MS` in sync_ratio.

### B2: fps counts frames instead of intervals

1. **Nudge:** A 40 ms camera should be exactly 25 fps. Why does EP-01 show more?
2. **Area:** Look at how fps is derived from frames and duration in camera_stats.
3. **Exact:** Use (frames - 1) / (duration_ms / 1000).

### B3: Any non-blank success string counts as a success

1. **Nudge:** pick shows a 1.0 success rate. Count the success column for the valid pick episodes.
2. **Area:** Follow how the `success` cell becomes a bool.
3. **Exact:** parse_bool should return clean(value).lower() in TRUTHY.

### B4: Recorded time floored to whole seconds

1. **Nudge:** Every recorded_s value is a whole number. Is that plausible for 2.07 s episodes?
2. **Area:** Look at the ms-to-seconds conversion in task_metrics.
3. **Exact:** Use recorded_ms / 1000, not //.

### B5: Blank tags split into an empty tag

1. **Nudge:** Where does the empty-string key in tag_counts come from?
2. **Area:** Look at what split_tags returns for a blank cell.
3. **Exact:** Return [] when the cleaned text is empty (`... if text else []`).

### B6: Operator counts include rejected episodes

1. **Nudge:** carol shows 3 episodes, but only one of hers is valid.
2. **Area:** Compare which list each Counter in summarize iterates over.
3. **Exact:** Count over `valid`, not `episodes`.

## "Why did that fix work?" probes

**B1**
- Why did EP-11, which sits right at the 0.9 threshold, keep its ratio?
- Why does EP-03 stay valid with or without the fix?

**B2**
- Why does the error shrink for longer episodes?
- Why didn't this change any episode's validity?

**B3**
- Why was wipe's success rate unaffected?
- Which other values in this CSV would bool() get right by accident?

**B4**
- Why doesn't round(..., 2) rescue the value?
- Where else in the code is milliseconds converted to seconds, and why is that one fine?

**B5**
- Why did EP-07's single-space cell end up the same as the truly blank ones?
- Would `if tag.strip()` inside the comprehension also work? Is it equivalent?

**B6**
- Why was dave's count right anyway?
- Which summary field is meant to look at invalid episodes, and how does it get them?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `robolog/sync.py` → `nearest_offset`: bisect_left returns the insertion point, so the closest sample is either just before it (i - 1) or at it (i). The bounds check handles t before the first or after the last sample, and `gap < best` is fine because equal gaps give the same distance either way.
