# set-053 interviewer notes

**Scenario:** Compare reviewer-corrected boxes (xyxy) with model pre-labels (COCO xywh) by box id: accepted at IoU >= 0.9 on continuous coordinates, otherwise adjusted, relabeled or deleted. Test 2 lists added and out-of-bounds boxes.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Zero coordinate treated as blank

1. **Nudge:** img-03/B5 shows deleted, but reviews.csv has a row for it. What is special about that row?
2. **Area:** Look at how load_reviews decides a row has a blank coordinate.
3. **Exact:** `not all(coords)` is true for 0.0; use any(c is None for c in coords).

### B2: Pixel-inclusive +1 on continuous coordinates

1. **Nudge:** img-05/B8 is accepted. Work out its IoU by hand from the data.
2. **Area:** Check how widths and heights are computed in geometry.py against the README's geometry section.
3. **Exact:** span() returns hi - lo + 1; it should be hi - lo.

### B3: Clipping mutates the reviewer's original boxes

1. **Nudge:** out_of_bounds is empty, but img-09/B15 clearly goes past x = 640 in reviews.csv. What does the box look like when the check runs?
2. **Area:** evaluate() keeps `revs` for the check and `clipped` for IoU. Are they really different boxes?
3. **Exact:** clip_to_image uses copy.copy(boxes); it needs copy.deepcopy(boxes).

## "Why did that fix work?" probes

**B1**
- Why does parse_coord return None for blanks instead of 0.0, and why does that matter here?
- Which other values would `all()` treat as missing?

**B2**
- Why did only one box change category when every IoU moved?
- Does the +1 make IoU larger or smaller for overlapping boxes, and why?

**B3**
- Why didn't any outcome change even though the boxes were mutated?
- What other fix (in clip_to_image's loop) would work without deepcopy?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `prelabelqa/geometry.py` → `is_out_of_bounds`: Strict comparisons are right for continuous coordinates: a box with x_max == width (img-05/B9 ends at 800) sits exactly on the edge and is inside, as the README says. `>=` would wrongly flag it.
