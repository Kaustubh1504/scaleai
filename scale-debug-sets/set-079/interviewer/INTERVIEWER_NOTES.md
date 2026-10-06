# set-079 interviewer notes

**Scenario:** Free-text judge replies (JSON, Score: N/D, verdicts) are normalised to 0-1, combined per sample by median, and rolled up into a category-weighted leaderboard and per-category means. Test 2 holds the leaderboard and category table.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Malformed JSONL line silently skipped

1. **Nudge:** Which failure is missing, and what is special about that line of the file?
2. **Area:** Look at what load_judgments does when json.loads raises.
3. **Exact:** Record it: failures.append(f"line-{n}") before `continue`.

### B2: Leaderboard averages display-rounded scores

1. **Nudge:** Each leaderboard value is off by about 0.001. Recompute atlas-7b by hand from the judge replies.
2. **Area:** Which sample-score mapping does the leaderboard use, and how was it built?
3. **Exact:** Pass the unrounded `scores` to weighted_mean, not `shown`.

### B3: group_by's default dict shared across calls

1. **Nudge:** Where do the model names in the category table come from?
2. **Area:** Look at group_by's signature and what happens on its second call.
3. **Exact:** Use `into=None` and create a fresh dict inside the function.

## "Why did that fix work?" probes

**B1**
- Why did s11's score stay correct with this line silently dropped?
- When is swallowing an exception acceptable, and what should you always do instead of a bare `continue`?

**B2**
- Why does the category table not show the same drift?
- Name a case where rounding early would change a ranking, not just a value.

**B3**
- Why is the leaderboard still right even though its groups are shared?
- If you ran only test_2 on its own, would the category `n` values be different from a full-suite run? Why?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `judgescore/parsing.py` → `extract_fraction`: The regex looks fragile, but it accepts both 'Score' and 'Rating', ':' or '=', decimals and spaces around '/', and requires the keyword. That is exactly README rule 2, and every fraction-style reply in the data parses.
- `judgescore/aggregate.py` → `median`: `(n - 1) // 2` looks like an off-by-one, but for odd n it is the middle index and for even n it is the lower of the two middle indices, which are then averaged. For n = 2 that gives the mean of both, and for n = 1 the single value.
