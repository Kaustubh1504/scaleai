# set-077 interviewer notes

**Scenario:** Two detection models' normalised centre-format predictions are converted to pixels and greedily matched (IoU >= 0.5, same label) against reviewer ground truth. Each model is scored independently, and Test 2 reports precision/recall/F1, auto-accept images and the best model.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Area computed with inclusive +1

1. **Nudge:** yolo-s loses two matches whose boxes overlap the ground truth by about half. Compute their IoU by hand from the README.
2. **Area:** Compare area() with the README's geometry section.
3. **Exact:** Remove the + 1 from both factors in area().

### B2: Shallow copy of the ground-truth pool

1. **Nudge:** yolo-s gets FPs on images where its boxes are perfect, but only on images detr-v2 already matched. What do the two models share?
2. **Area:** Look at the 'copy' evaluate_model makes before matching, and at what match_image does to the pool.
3. **Exact:** dict(ground_truth) is shallow. Copy each list: {image: list(boxes) for image, boxes in ground_truth.items()}.

### B3: IoU threshold made strict

1. **Nudge:** After the area fix, one yolo-s image is still a miss. What is its IoU exactly?
2. **Area:** Check the threshold comparison in match_image against rule 2.
3. **Exact:** Use `overlap >= IOU_THRESHOLD`.

## "Why did that fix work?" probes

**B1**
- Why did the large boxes still match while the small ones flipped?
- Why does a +1 in area but not in the intersection always lower IoU?

**B2**
- Why did detr-v2's auto_accept change too, even though detr-v2 is evaluated first?
- Would copy.copy(ground_truth) have fixed it? What about copy.deepcopy?

**B3**
- Why was this invisible while area() added +1?
- Why can this data test an exact 0.5 boundary with floats (what is special about 128/512 and 64/512)?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `prelabel/geometry.py` → `from_normalized_center`: The halving and the width/height scaling look easy to get backwards, but this is exactly the README formula for continuous pixel edges. No +1 is needed because edges are not inclusive pixel indices.
- `prelabel/matching.py` → `pick_best`: The key (iou, -index) looks odd, but max() then takes the highest IoU and, among equal IoUs, the smallest index, which is the earliest ground-truth box as rule 2 requires.
