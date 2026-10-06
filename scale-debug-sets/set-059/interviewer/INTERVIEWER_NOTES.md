# set-059 interviewer notes

**Scenario:** Pairwise rater judgements (some from a legacy UI that swapped positions) are cleaned, deduped per rater/prompt/pair, and turned into win rates, Elo (K=32) and a list of contested prompts. Test 2 is the leaderboard and disagreement list.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Comparison rater ids not lower-cased

1. **Nudge:** used is 18, not 22. Which rows went missing, and what do they have in common?
2. **Area:** Compare how rater ids are cleaned in load_raters and read_comparisons.
3. **Exact:** Lower-case the comparison rater: row["rater"].strip().lower().

### B2: swapped = "false" treated as swapped

1. **Nudge:** Look at R07's p06 and p08 rows. Who should have won each?
2. **Area:** Look at how the swapped column is interpreted.
3. **Exact:** Use row["swapped"].strip().lower() in TRUE_WORDS.

### B3: groupby over unsorted comparisons

1. **Nudge:** p04 and p10 are found but p03 isn't. Where are p03's rows in the kept list?
2. **Area:** Look at how contested() groups comparisons.
3. **Exact:** Sort by _group_key before calling groupby.

## "Why did that fix work?" probes

**B1**
- Why is r07 in the qualified set even though raters.json has a trailing space?
- Why were these rows dropped silently instead of raising an error?

**B2**
- Why was this invisible until rater ids were fixed?
- Why did R07's 'true'/'TRUE' rows come out right even with this change?

**B3**
- Why did p04 and p10 still come out right?
- What would a dict/defaultdict version look like, and why doesn't it need sorting?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `prefrank/ratings.py` → `expected`: The exponent (rb - ra) looks reversed, but when ra > rb it is negative, 10**negative < 1 and the result is above 0.5, so the stronger player is favoured, as the Elo formula in the README says.
