# set-063 interviewer notes

**Scenario:** Convert raw support-chat turns into system/user/assistant SFT examples: map and merge roles, trim to user-first/assistant-last, drop the oldest exchange until the example fits max_tokens, and hold back excluded tags.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Blank tag cells produce an empty tag

1. **Nudge:** Where does the empty-string key in tag_counts come from?
2. **Area:** Look at what parse_tags returns for a blank cell and for `coding;billing ;`.
3. **Exact:** Filter out empty entries: `... for t in clean(raw).split(";") if t.strip()`.

### B2: Budget loop config reads the generation limit

1. **Nudge:** c03 has 86 tokens with a 60-token budget, yet nothing was dropped. What budget is the code using?
2. **Area:** Look at how load_config builds the settings dict, and compare with config.json.
3. **Exact:** Read `raw["max_tokens"]`, not `raw["max_new_tokens"]`.

### B3: Truncation drops one message instead of an exchange

1. **Nudge:** After truncation, what role is the first non-system message in c10?
2. **Area:** Look at the slice inside fit_to_budget's loop.
3. **Exact:** Drop a whole exchange: `body = body[2:]`.

## "Why did that fix work?" probes

**B1**
- Why did `tags or [DEFAULT_TAG]` stop working?
- Why is count_tokens' `.split()` safe while this `.split(";")` is not?

**B2**
- Why was the truncation loop impossible to test while this was wrong?
- How would you make a config mix-up like this fail loudly?

**B3**
- Why did c03 end up with the right messages but the wrong dropped_messages?
- Why was this invisible until the budget came from the right config key?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `turnsmith/budget.py` → `count_tokens`: `str.split()` with no argument splits on any whitespace run and returns [] for an empty string, so it counts words exactly as rule 5 says. It looks like a cousin of the tag-splitting code, but only `split(";")` produces empty entries.
