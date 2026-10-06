# set-009 interviewer notes

**Scenario:** Convert inclusive-end character spans from three annotators to half-open offsets, reject spans whose text doesn't match their quote, drop each annotator's overlapped shorter spans, then keep spans that at least two annotators agree on.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Inclusive end not converted

1. **Nudge:** Every single span is reported as misaligned. Pick one and slice the text by hand.
2. **Area:** Compare README rules 1-2 with how load_spans builds `end`.
3. **Exact:** Use `end=end + 1` to convert the inclusive end to half-open.

### B2: List shrunk while looping over it

1. **Nudge:** ann-c keeps two overlapping spans on d10. Which one should have been dropped?
2. **Area:** Look at the loop in resolve_overlaps. What happens to the iteration after `spans.remove`?
3. **Exact:** Iterate over a copy: `for span in list(spans):`.

### B3: Doc loop returns on the first unannotated doc

1. **Nudge:** Only d01 and d02 have entities. What is special about the next doc id?
2. **Area:** Look at what build_entities does with a document that has no spans.
3. **Exact:** Skip the document with `continue` instead of returning.

## "Why did that fix work?" probes

**B1**
- Why did fixing this make new failures appear in Test 2?
- If the export had been half-open already, which spans would have looked wrong instead?

**B2**
- Why was 'Nokia' dropped correctly but not 'Ericsson'?
- Give another way to write this without removing from a list at all.

**B3**
- Why was this invisible while every span was misaligned?
- Which data change would have hidden this bug entirely?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `spanmerge/spans.py` → `overlaps`: Strict `<` looks as if it might miss touching spans, but with half-open offsets `[0, 5)` and `[5, 9)` share no character, and README rule 5 says touching spans do not overlap.
