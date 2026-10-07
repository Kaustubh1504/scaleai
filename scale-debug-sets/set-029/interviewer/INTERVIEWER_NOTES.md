# set-029 interviewer notes

**Scenario:** Annotator boxes exported as xywh are matched greedily (highest IoU first) to xyxy ground truth with per-class IoU thresholds; the report scores each annotator and gives per-class best-IoU localisation.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Matching takes the weakest overlap first

1. **Nudge:** Compare p01's IoU with g01 and with g02. Which pairing did the code choose?
2. **Area:** Look at the order candidates are processed in match().
3. **Exact:** Sort with reverse=True (highest IoU first).

### B2: Annotator ids not lower-cased

1. **Nudge:** How many annotators does the report list, and how many should there be?
2. **Area:** Compare how the loader cleans annotator ids with the README.
3. **Exact:** Add .lower() to the annotator id.

### B3: Pixel-inclusive +1 in the intersection

1. **Nudge:** Localisation is higher than it should be for every class. Compute IoU(p17, g07) by hand.
2. **Area:** Check iou() against the coordinate convention in the README.
3. **Exact:** Remove the + 1 from iw and ih.

## "Why did that fix work?" probes

**B1**
- Why are tp/fp/fn identical under both orders in this data?
- Construct a case where the wrong order changes the tp count.

**B2**
- Why did matches not change even though the ids were split?
- What data change would have made this alter the matches too?

**B3**
- Why can this version produce an IoU above 1?
- Why did no match decision change? Which pairs came closest to a threshold?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `boxaudit/matching.py` → `best_iou_per_gt`: Pooling every annotator's predictions looks like a scoping slip, but the README defines localisation as the best IoU any annotator reaches, ignoring thresholds and matching. max(..., default=0.0) covers boxes nobody predicted (g10).
- `boxaudit/loader.py` → `xywh_to_xyxy`: With exclusive right/bottom edges, x2 = x + w exactly. No ±1 is needed in this convention.
