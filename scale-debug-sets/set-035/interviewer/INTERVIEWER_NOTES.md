# set-035 interviewer notes

**Scenario:** Raters compared model pairs across 12 collection rounds. Filter skipped, failed-rater and invalid comparisons, compute win rates with half-credit ties, run sequential Elo in numeric round order, and list models with at least 11 games.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Counter.update on a model name counts its letters

1. **Nudge:** Every win rate equals half its tie share. Where did the wins go?
2. **Area:** Print the `wins` Counter inside win_rates.
3. **Exact:** Use wins[comp.winner] += 1 (or wins.update([comp.winner])).

### B2: Round kept as text, so 10-12 sort before 2

1. **Nudge:** Win rates are right but all Elo values are a little off. Elo depends on more than the counts. On what?
2. **Area:** Check the type of Comparison.round when elo_ratings sorts by it.
3. **Exact:** Parse the round with int(...) in load_comparisons.

### B3: Model with exactly the minimum games left off

1. **Nudge:** Which model is missing from the leaderboard, and how many games did it play?
2. **Area:** Compare the eligibility filter with README rule 10.
3. **Exact:** Use games[m] >= MIN_GAMES.

## "Why did that fix work?" probes

**B1**
- Why does games.update(comp.models) work while wins.update(comp.winner) doesn't?
- Why did Elo stay correct while this was present?

**B2**
- Why didn't the sum of ratings change?
- Would sorting by comparison_id have been safe instead? Why not?

**B3**
- m-eps is also missing in the expected output. Why is that correct?
- What single data point would you add to a test to pin down this boundary?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `prefrank/elo.py` → `expected_score`: `opponent - rating` in the exponent looks reversed, but it is the standard Elo formula from README rule 8: a stronger opponent makes the exponent positive and the expected score drop below 0.5.
