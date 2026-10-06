# set-005 interviewer notes

**Scenario:** Match annotator boxes to ground truth per image (same label, IoU >= 0.5, greedy best-first), using inclusive pixel coordinates. Flag image/annotator pairs with recall < 0.8 and summarise per annotator.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Box area computed with exclusive coordinates

1. **Nudge:** Work out img_03/alice's IoU by hand from the CSV. Is it above 0.5?
2. **Area:** Compare area() and intersection() in geometry.py. Do they count pixels the same way?
3. **Exact:** area() needs + 1 on both width and height: (x_max - x_min + 1) * (y_max - y_min + 1).

### B2: Matched-box sets shared across image/annotator pairs

1. **Nudge:** The first result is right and later ones drift. What carries over between iterations?
2. **Area:** Look at where evaluate creates its per-pair bookkeeping.
3. **Exact:** Move `matched_pred, matched_gt = set(), set()` inside the for loop.

### B3: groupby over unsorted results

1. **Nudge:** Every annotator reviewed 1 image? Check that against Test 1's keys.
2. **Area:** Look at what order annotator_summary receives results in, and what groupby assumes.
3. **Exact:** Sort by annotator before groupby (or accumulate into a dict).

## "Why did that fix work?" probes

**B1**
- Why did the large boxes on img_01 and img_05 still match correctly with the broken area?
- If the data were in exclusive coordinates (x_max is one past the last pixel), which functions would change?

**B2**
- Why was the very first image/annotator pair still correct?
- If the sets held Box objects instead of indices, would the bug still show? (Hint: frozen dataclasses with equal fields compare equal.)

**B3**
- Why does the output look plausible (no crash, sensible precision) even though it's wrong?
- How would a defaultdict accumulator avoid this whole class of problem?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `boxqa/matching.py` → `greedy_match`: Sorting (-iou, i, j) ascending gives best IoU first, with ties going to the earlier annotator box and then the earlier ground-truth box, which is exactly the spec. The `>=` threshold is also the spec. It looks like the obvious place for a matching problem, but it has none.
- `boxqa/loader.py` → `within_cutoff`: `<=` keeps annotations submitted on the cutoff day, which the spec requires ('on or before'). Alice's img_05 rows are dated exactly 2026-05-10 and must count.
