# set-015 interviewer notes

**Scenario:** Normalise vendor chat transcripts (role aliases, merged turns, order checks), truncate to a token budget by dropping the oldest user/assistant pairs, render the training template and summarise tags.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Numeric 0 content treated as missing

1. **Nudge:** c03 is rejected as empty_message. Look at its assistant message in the data.
2. **Area:** Look at how loader.clean_content handles values that are not strings.
3. **Exact:** Only treat None as empty: `if value is None: return ""`, then `str(value).strip()`.

### B2: Rendered parts accumulate across examples

1. **Nudge:** c05's text starts with the math tutor prompt from c01. Where does that come from?
2. **Area:** Look at the parts argument of render().
3. **Exact:** Default to None and create a new list inside: `parts = [] if parts is None else parts`.

### B3: Blank tags counted as a tag

1. **Nudge:** tag_counts has a key that is an empty string. Which conversations produce it?
2. **Area:** Look at split_tags in reports.py, and try "".split(",") in a REPL.
3. **Exact:** Keep only non-empty pieces: add `if t.strip()` to the comprehension.

## "Why did that fix work?" probes

**B1**
- Which other JSON values would `or ""` also have swallowed?
- Why did c10 stay rejected after the fix?

**B2**
- Why were the token counts right even though the text was not?
- Would c01's text have looked right with this bug? Why?

**B3**
- Why does "".split() (no argument) behave differently from "".split(",")?
- Why are rejected conversations' tags counted here at all?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `sftpack/turns.py` → `truncate`: `body[2:]` drops exactly one user/assistant pair (the body always alternates after check_order), the system message is kept outside the loop, and `len(body) > 2` stops before the last pair, after which a still-too-long example is rejected, as rules 5 and 6 say.
