# set-083 interviewer notes

**Scenario:** Screen labelers on a calibration round, convert position-relative 1-7 ratings into margins in favour of model A, aggregate per pair into A/B/tie verdicts, export chosen/rejected training pairs and rank models by win rate with an alphabetical tie-break.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Calibration judgements not deduplicated

1. **Nudge:** lab-09 has 5 checks, but there are only 4 calibration pairs. How?
2. **Area:** Compare how the two judgement files are prepared in build_report.
3. **Exact:** Wrap the calibration load in latest_only(...) as for judgements.csv.

### B2: left_model compared without normalising

1. **Nudge:** Only P08's margin is off. Recompute its three judgements by hand.
2. **Area:** Look at how margin_of decides which model was on the left.
3. **Exact:** Compare norm_model(judgement.left_model) with pair.model_a.

### B3: reverse=True also reverses the name tie-break

1. **Nudge:** The numbers are all right. Which two rows are out of order, and what do they share?
2. **Area:** Look at the sort in standings.
3. **Exact:** Negate win_rate in the key and drop reverse=True.

## "Why did that fix work?" probes

**B1**
- Why does excluding lab-09 change none of the verdicts?
- Which of lab-09's two C2 submissions should count, and why?

**B2**
- Why does P08's verdict still come out as A?
- Why is calibration unaffected by the same function?

**B3**
- Why doesn't reverse=True work for a mixed descending/ascending sort?
- How else could you sort descending by one field and ascending by another?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `prefpairs/aggregate.py` → `a_margin`: The two branches look reversed, but a low rating means the left response won, so 4 - rating is positive exactly when the left (model_a) response is preferred; when model_b was on the left the sign flips.
- `prefpairs/aggregate.py` → `verdict_for`: `abs(margin) < 0.5` matches the spec: only values strictly inside the band are ties, so P06's 0.5 is decided for A.
