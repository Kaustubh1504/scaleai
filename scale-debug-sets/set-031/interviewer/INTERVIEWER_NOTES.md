# set-031 interviewer notes

**Scenario:** Two models answered a weighted multiple-choice bank with harness retries. Pick the highest-numbered ok attempt per (model, item), parse the last Answer marker, and score weighted accuracy with failed items kept in the denominator.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Status enum compared to plain strings

1. **Nudge:** Atlas Q08 has an ok 'Answer: C' attempt, yet it shows up as unparsed. Which attempt was graded?
2. **Area:** Look at how select_final decides an attempt is not a candidate.
3. **Exact:** `att.status in ("error", "timeout")` compares an Enum to strings. Use (Status.ERROR, Status.TIMEOUT).

### B2: Timeout check always true

1. **Nudge:** Every error row is being counted as a timeout. Where are status strings turned into Status values?
2. **Area:** Read the timeout branch of parse_status slowly.
3. **Exact:** Write `text == "timeout" or text == "timed_out"` (or `text in (...)`).

### B3: Failed items dropped from the denominator

1. **Nudge:** Correct lists now match, but both accuracies are too high. What do you get dividing earned weight by the whole bank?
2. **Area:** Look at where `possible` is accumulated in score_model, relative to the failed branch.
3. **Exact:** Move `score.possible += item.weight` above the `if final is None:` check.

## "Why did that fix work?" probes

**B1**
- Why would this comparison have worked if Status were declared as `class Status(str, Enum)`?
- Why did the failed lists become empty instead of just changing?

**B2**
- Why didn't any model's accuracy change while this was present?
- What would `if text == ("timeout" or "timed_out")` have done instead?

**B3**
- Why was this invisible until the status comparison in select_final was fixed?
- by_category was right the whole time. Why?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `evalscore/parsing.py` → `parse_choice`: Taking matches[-1] looks like it should be the first match, but README rule 3 says the last Answer marker wins because models revise themselves. The negative lookahead stops words like 'Definitely' from being read as a D, and the bare-letter fallback uses fullmatch so it only fires on outputs that are a lone letter.
