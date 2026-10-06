# set-039 interviewer notes

**Scenario:** Chat logs become SFT examples: roles normalised, bad conversations rejected, default system prompt added, oldest turns trimmed to a token budget, and assistant-content character spans recorded for the loss mask.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Assistant span starts on the header newline

1. **Nudge:** Print text[s:e] for one span. What is the first character?
2. **Area:** Compare how block() builds the header with how assistant_spans skips it.
3. **Exact:** Skip the newline too: offset + len(tag(message)) + 1.

### B2: Trimming edits the caller's message list

1. **Nudge:** c07 was clearly trimmed (20 tokens). Why does turns_dropped say 0?
2. **Area:** What does build_examples compare to get turns_dropped, and what does truncate do to its argument?
3. **Exact:** Copy before deleting: kept = list(messages).

### B3: Role enum compared with a string

1. **Nudge:** assistant_turns is 0 although every example has an assistant reply.
2. **Area:** What type is m.role? What does it compare equal to?
3. **Exact:** Compare with Role.ASSISTANT (or m.role.value == 'assistant').

## "Why did that fix work?" probes

**B1**
- Why is the span length still right but the content wrong?
- How would you compute the span so it can't drift from block()?

**B2**
- Why are the token counts still right?
- Would a shallow copy be enough if truncate changed message content instead of removing messages?

**B3**
- Would class Role(str, Enum) have avoided this? What would you give up?
- Where else in the package are roles compared, and how?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `sftfmt/render.py` → `fits`: `<=` looks like a boundary slip, but the README says an example of exactly max_tokens fits. truncate uses fits both for the loop and for the final too_long check, so the boundary is consistent.
