# set-055 interviewer notes

**Scenario:** Pick the latest successful attempt per model and item, extract the chosen letter from free-text output (last answer marker wins), grade it, and rank models by weighted score with a correct-count tie-break. Test 2 is the report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: `== "ok" or "cached"` is always true

1. **Nudge:** delta's I05 and I09 never succeeded, yet they're listed as unparsed rather than errored. Which attempt was chosen for them?
2. **Area:** Look at the status filter in latest_success.
3. **Exact:** `att.status == "ok" or "cached"` is always truthy; use att.status in ("ok", "cached").

### B2: Zero weight replaced by the default

1. **Nudge:** Every score shrank, and alpha's shrank by less than you'd expect. What is the total weight?
2. **Area:** Look at how a weight is chosen when the CSV cell is 0 versus blank.
3. **Exact:** Use DEFAULT_WEIGHT only when to_int returned None.

### B3: Score ties broken by name only

1. **Nudge:** bravo and charlie have the same weighted score. What does the README say about ties?
2. **Area:** Look at the sort key for the leaderboard.
3. **Exact:** Add -len(correct[m]) before the name in the key.

## "Why did that fix work?" probes

**B1**
- Why didn't any score or correct list change?
- What data would have made this bug change a correct answer into an unparsed one?

**B2**
- Why didn't the leaderboard order change?
- to_int already separates blank from 0. Why was that information lost?

**B3**
- Why does each key component need a minus sign except the name?
- How could the two models tie on weight with such different correct counts?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `evalscore/parsing.py` → `extract_choice`: Taking matches[-1] looks backwards, but the README says the last answer marker wins. delta's I08 ('First guess: answer is A. On reflection, Answer = C') depends on it. JSON is only tried when the output starts with '{', as the spec says.
