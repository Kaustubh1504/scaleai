# set-007 interviewer notes

**Scenario:** Extract the final answer letter from raw model outputs, flag missing or changed answers, grade against weighted gold items, and rank three models on a leaderboard with a latency tie-break.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Flag list is a shared default

1. **Nudge:** Every response has the same flags, including clean ones like r01. Where do the flag lists come from?
2. **Area:** Look at the signature of parse_output.
3. **Exact:** Use `flags=None` and create a new list inside the function when it is None.

### B2: Category counter fed a string

1. **Nudge:** by_category has single letters as keys. What produced them?
2. **Area:** Look at how model_stats fills the category Counter.
3. **Exact:** Use `by_category[r["category"]] += 1` (or `update([category])`).

### B3: Accuracy ties broken by name only

1. **Nudge:** The top two models have the same accuracy. How should the tie be broken?
2. **Area:** Compare the leaderboard sort key with README rule 6.
3. **Exact:** Add `kv[1]["mean_latency_ms"]` between accuracy and name in the key.

## "Why did that fix work?" probes

**B1**
- Why do all responses show the full list, not just the ones parsed after the first flag?
- Why are answers and correctness unaffected?

**B2**
- What would `Counter("logic")` return?
- Why did accuracy stay correct while this was happening?

**B3**
- Why is accuracy negated but latency not?
- Which test would you add so a missing tie-break is caught even if names happen to sort the same way?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `evalscore/parsing.py` → `last_answer`: Taking `matches[-1]` looks like it might skip the model's first answer, but README rule 2 says the last tag is the answer. r03, r23 and r35 revise themselves and are graded on the final letter.
