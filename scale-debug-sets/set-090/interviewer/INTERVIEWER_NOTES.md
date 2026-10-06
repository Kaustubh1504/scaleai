# set-090 interviewer notes

**Scenario:** Validate teleoperation episodes with ordered checks (robot registry, calibration, required streams, duration, frame gaps, camera/joint sync, label). Streams come in mixed units and per-robot clock offsets. The report covers per-task usable data, success rates and operator stats.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Episode robot ids not lower-cased

1. **Nudge:** R-02 is in robots.json, so why are E03 and E04 unknown_robot?
2. **Area:** Compare how robot ids are normalised in load_robots and in load_episodes.
3. **Exact:** load_episodes should use norm(row["robot_id"]).

### B2: Joint timestamps left in seconds

1. **Nudge:** E05 and E06 are out_of_sync. What is special about their lines in frames.jsonl?
2. **Area:** Follow the joint timestamps through prepare() and compare them with the camera path.
3. **Exact:** joints_ms should be to_ms(streams.get("joints", []), unit).

### B3: Joint stream shifted by the camera offset

1. **Nudge:** Which robot's episodes fail sync, and how does its entry in robots.json differ from the others?
2. **Area:** Look at which offset is added to each stream in prepare().
3. **Exact:** The joints line should add robot.joint_offset_ms.

### B4: Camera period truncated

1. **Nudge:** E07's largest camera gap is 166 ms. What limit applies to a 15 Hz camera?
2. **Area:** Look at how the gap limit is computed.
3. **Exact:** Use true division: GAP_FACTOR * 1000 / robot.camera_hz.

### B5: Operator valid count includes failed checks

1. **Nudge:** ana's valid_s is 8.0, but her valid episodes add up to 5.0. Which extra episodes are included?
2. **Area:** Look at the condition operator_table uses to count an episode as valid.
3. **Exact:** Use `if v.valid:`.

### B6: 0.0 success rate reported as None

1. **Nudge:** fold_towel has a valid episode, so why is its rate None?
2. **Area:** Look at the expression that builds each rate.
3. **Exact:** Remove the `or None`.

## "Why did that fix work?" probes

**B1**
- Why does E10's ` r-05` still match with this bug?
- After the fix, E03 and E04 fail a different check. Why couldn't you see that before?

**B2**
- Why did the duration check pass for E05 even though one stream was in the wrong unit?
- Which episodes would break if the camera conversion were skipped instead?

**B3**
- Why was this invisible until robot ids were normalised?
- r-08 has equal camera and joint offsets. Would it ever expose this?

**B4**
- Why does E08 fail dropped_frames either way?
- Why do the 10 Hz robots never show this?

**B5**
- Why does the task table not have the same problem?
- Which operator would still be right with this bug, and why?

**B6**
- Can this function ever produce a division by zero? Why not?
- When would returning None be the right answer for a task?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `episodeqa/streams.py` → `drop_repeats`: It sorts first, so repeated timestamps end up next to each other, and then skips any value equal to the last one kept. Comparing with out[-1] is the standard way to dedupe a sorted sequence; E01's repeated frame is removed exactly once.
- `episodeqa/sync.py` → `nearest_gap`: bisect_left gives the insertion point i. The closest value is always at i-1 or i, and both are checked with bounds guards, so the edges of the stream and exact matches are handled. The loop over (i - 1, i) looks like an off-by-one, but it is correct.
