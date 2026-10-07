# set-057 interviewer notes

**Scenario:** Annotator NER spans from two tools (legacy: 1-based inclusive; v2: 0-based exclusive) are converted, trimmed, voted on (2 distinct annotators needed), and overlap-resolved by votes then length. Test 2 checks summary counts.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Legacy end shifted as if it were 1-based exclusive

1. **Nudge:** Every D04 entity is one character short. Which tool produced D04's spans?
2. **Area:** Work the README's Paris example through to_zero_based by hand.
3. **Exact:** Only start moves: return start - 1, end.

### B2: Equal-vote overlaps prefer the shorter span

1. **Nudge:** D02 keeps 'Morgan' as PER. How many votes did each overlapping candidate get?
2. **Area:** Look at the ranking key in resolve_doc against the README overlap rule: which span should win an equal-vote overlap?
3. **Exact:** The sort key uses `e.length`; it should be `-e.length` so the longer span ranks first.

### B3: `== "PER" or "ORG"` counts every entity

1. **Nudge:** named_entities equals the total entity count. Is that plausible?
2. **Area:** Look at the condition in the named_entities sum.
3. **Exact:** Compare against both labels: ent[2] in ("PER", "ORG").

## "Why did that fix work?" probes

**B1**
- Why did Lima disappear entirely instead of just losing a character?
- Why is a 1-based inclusive end equal to a 0-based exclusive end?

**B2**
- If PER Morgan had 3 votes, would the length key matter for D02?
- Why didn't named_entities change even though the label did?

**B3**
- How does Python group `a == b or c`?
- Why didn't any Test 1 assertion notice?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `spanmerge/spans.py` → `trim_span`: `text[end - 1]` looks like an off-by-one, but end is exclusive, so the last character of the span is at end - 1. Both loops stop when start meets end, so an all-whitespace span collapses to empty and is dropped by make_span.
