# set-081 interviewer notes

**Scenario:** Clean sloppy character-range NER selections (trim whitespace, resolve label aliases, snap to token boundaries, dedupe), export spans for non-gold documents and score each annotator against adjudicated gold spans with exact-match P/R/F1 plus a label-confusion table.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Snap covers the token that starts at the span end

1. **Nudge:** Which exported spans changed, and what character follows each of them in the text?
2. **Area:** Look at how snap decides whether a token is covered by the selection.
3. **Exact:** In snap, `t.start <= end` should be `t.start < end` (end is exclusive).

### B2: Non-gold spans scored as false positives

1. **Nudge:** Where does ann-d's row come from? Which documents did ann-d annotate?
2. **Area:** Compare the list score_annotators builds with the list it actually iterates over.
3. **Exact:** Loop over `scored`, not `spans`, when filling predicted/docs_seen.

### B3: Confusion ties left in insertion order

1. **Nudge:** The counts are right; only the order of two rows differs. What do those rows have in common?
2. **Area:** Look at how rank_confusions orders the Counter.
3. **Exact:** Replace most_common() with sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])).

## "Why did that fix work?" probes

**B1**
- Why did "Liam O'Brien" and "Hannah Becker" keep their offsets while "Milan" moved?
- Why don't the gold-document scores change with this slip, even though snapping runs on every span?

**B2**
- Why did tp and fn stay the same for ann-a while fp grew?
- Why is the confusion table unaffected even though it also reads every span?

**B3**
- What order does Counter.most_common use for equal counts, and why is that fragile?
- If ann-b's rows came first in the CSV, would the test have passed with the old code?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `spanalign/tokens.py` → `tokenize`: finditer's m.end() is already end-exclusive, matching the span convention, and the pattern keeps inner apostrophes (O'Brien) and splits punctuation into single tokens exactly as the README describes.
- `spanalign/spans.py` → `trim_whitespace`: The arithmetic looks backwards, but lstrip measures the leading whitespace (added to start) and rstrip the trailing whitespace (subtracted from end). An all-whitespace selection makes start >= end and is rejected as empty.
