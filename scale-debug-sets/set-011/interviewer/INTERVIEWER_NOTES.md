# set-011 interviewer notes

**Scenario:** Turn pairwise human preference judgements (a / b / tie / draw / both_bad) into per-model win rates, sequential Elo ratings and a leaderboard of models with at least 4 games.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: both_bad counted as a tie

1. **Nudge:** Cirrus has one tie in the data but the table shows more. Which rows are being counted as ties?
2. **Area:** Look at the branch in winrates.py that handles tie and draw.
3. **Exact:** `c.winner == "tie" or "draw"` is always true. Use `c.winner == "tie" or c.winner == "draw"` (or `in ("tie", "draw")`).

### B2: Ratings rounded to whole numbers on every update

1. **Nudge:** Every Elo value is a whole number. Where could the decimals be lost?
2. **Area:** Compare README rule 6 with how update() returns the new ratings.
3. **Exact:** update() rounds both ratings. Return `ra + delta, rb - delta` and leave rounding to the report.

### B3: Model with exactly 4 games left off the leaderboard

1. **Nudge:** Which model is missing from the leaderboard, and how many games did it play?
2. **Area:** Look at the eligibility filter in reports.leaderboard.
3. **Exact:** `stats.games > MIN_GAMES` should be `>= MIN_GAMES`.

## "Why did that fix work?" probes

**B1**
- Why didn't the Elo ratings change even though both_bad rows were treated as ties here?
- How does Python group `x == "tie" or "draw"`, and what does the `or` return?

**B2**
- Why is the answer not just the correct ratings rounded to the nearest integer?
- Why did the leaderboard order survive this rounding?

**B3**
- What data would you add to make sure a boundary like this is always exercised?
- delta-3b is also missing. Why is that one correct?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `prefrank/elo.py` → `expected_score`: The `(opponent - rating)` order looks reversed, but it is exactly the spec's 1 / (1 + 10^((R_B - R_A)/400)): a higher own rating makes the exponent negative and the expected score larger.
- `prefrank/loader.py` → `parse_rated_at`: It covers exactly the three timestamp formats the README lists, with month/day order for the slash format.
