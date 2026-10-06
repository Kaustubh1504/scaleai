# set-033 interviewer notes

**Scenario:** Annotators using brat (half-open offsets) and labelkit (inclusive end) marked PER/ORG/LOC spans. Spans are converted, trimmed and validated, accepted at 2+ distinct annotators, and Test 2 reports per-annotator invalid counts and agreement.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Entity text sliced one character too far

1. **Nudge:** Offsets are right but the text has an extra character. Where is the text cut out?
2. **Area:** Look at how entities_by_doc builds the `text` field.
3. **Exact:** Use doc.text[start:end]; the +1 belongs only to labelkit conversion, which already happened.

### B2: groupby over a partially sorted list

1. **Nudge:** D03 'Washington' has three PER votes in the CSV but reports 2. What sits between them?
2. **Area:** Look at the order vote() feeds into groupby.
3. **Exact:** Sort by the same key you group by: sorted(spans, key=lambda s: s.key).

### B3: Duplicate submissions counted twice in agreement

1. **Nudge:** Only a02 is off. What is special about a02's rows in spans.csv?
2. **Area:** Look at how agreement() collects each annotator's spans.
3. **Exact:** Use a set: per = defaultdict(set) and .add(span.key).

## "Why did that fix work?" probes

**B1**
- Why did Kyoto come out right even with the extra +1?
- How many places should know about labelkit's inclusive end, and why only one?

**B2**
- Why was the entity still accepted, just with fewer votes?
- What data would make this drop an entity completely?

**B3**
- Why didn't the duplicate inflate the votes for Naomi Osaka?
- Why does counting a duplicate push the rate up rather than down here?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `spanmerge/loader.py` → `to_exclusive_end`: The `end + 1` looks like the off-by-one, but the README says labelkit exports the index of the last character, so adding 1 is exactly what turns it into a half-open end. brat ends are already exclusive and pass through unchanged.
