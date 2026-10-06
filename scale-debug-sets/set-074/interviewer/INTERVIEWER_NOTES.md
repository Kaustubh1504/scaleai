# set-074 interviewer notes

**Scenario:** Measure each annotator's per-rubric bias on gold items (memoised per run), subtract it from their 1-5 ratings, and resolve each item by median with an agreement threshold. Test 3 summarises statuses per rubric.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Ratings on the closing day dropped

1. **Nudge:** I12 has 4 ratings in the export, yet it is insufficient. When were they submitted?
2. **Area:** Check the window comparison against README rule 2.
3. **Exact:** Use `<= config["closes"]` so the closing day counts.

### B2: Bias pools gold from both rubrics

1. **Nudge:** Every annotator has the same bias for v1 and v2. Is that plausible from the gold data?
2. **Area:** Which gold rows does compute_bias average?
3. **Exact:** Filter rows by items[r.item_id].rubric == rubric as well as by annotator.

### B3: Memo key ignores the rubric

1. **Nudge:** After B2, a01 still shows 1.0 for v2. Compute a01's v2 bias by hand from the gold rows.
2. **Area:** compute_bias gives the right answer when called directly. What sits between it and the report?
3. **Exact:** The memo key must include the rubric: (annotator_id, rubric).

### B4: Even-length median takes the upper pair

1. **Nudge:** Only items with 4 votes have the score off. What do they have in common?
2. **Area:** Work the median of [2, 2.5, 3, 3] by hand and compare with the code.
3. **Exact:** Use ordered[mid - 1] and ordered[mid] for the even case.

### B5: Agreement counter not reset per item

1. **Nudge:** Agreement is a fraction. How can it be 2.0?
2. **Area:** Follow `within` across loop iterations in resolve().
3. **Exact:** Reset `within = 0` inside the loop for each item.

### B6: groupby over unsorted results

1. **Nudge:** by_rubric adds up to 2 items, but there are 12. Where did the others go?
2. **Area:** What does groupby require of its input?
3. **Exact:** Sort the results by rubric before grouping.

## "Why did that fix work?" probes

**B1**
- Why was I10's 2026-06-15 00:05 rating correctly excluded both before and after the fix?
- Why does the bias table change when only the closing day is affected?

**B2**
- Why did a03 and a04 look correct even with this bug?
- After this fix, why does the table still show identical v1/v2 values for most annotators?

**B3**
- Why was this invisible while compute_bias ignored the rubric?
- Why does a02 come out with 0.0 for both rubrics rather than 0.5?

**B4**
- Why don't the 3- and 5-vote items change?
- With min_votes 3, why doesn't this ever raise IndexError?

**B5**
- Why is I01's agreement still right?
- Why did insufficient items not push the counter up?

**B6**
- Why would this pass if items.csv listed all v1 items first?
- Name a way to count per rubric that does not depend on order.

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `likert/utils.py` → `parse_submitted`: Epoch values look like they might be milliseconds, but the spec says epoch seconds, and fromtimestamp(..., tz=utc) followed by dropping tzinfo gives the naive UTC time that matches the text formats. The values decode to the same June 2026 window as the text timestamps.
- `likert/calibration.py` → `adjust`: Subtracting the bias looks backwards, but bias is mean(score - gold), so an annotator who rates high has a positive bias and score - bias pulls them back toward gold. The clamp keeps results on the 1-5 scale (I06: a03's 4 + 1 becomes 5).
