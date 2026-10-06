# set-017 interviewer notes

**Scenario:** Score each team's accepted submissions as a 1-decimal percentage, keep the best one, and rank teams highest-first with ties going to the team that reached the score earlier.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Percentage rounded before scaling

1. **Nudge:** Look closely at T02's and T05's scores in the failure output.
2. **Area:** Where is the percentage computed, and in what order are the operations done?
3. **Exact:** Scale first and round last: round(100 * correct / total, 1).

### B2: Accepted count includes rejected submissions

1. **Nudge:** Which teams have a count that is too high? What do their extra rows have in common?
2. **Area:** Look at what is counted when TeamStats is built.
3. **Exact:** Use len(accepted), not len(subs).

### B3: Score ties broken by team id

1. **Nudge:** Two teams in the middle of the board are swapped. What do they have in common?
2. **Area:** Look at the sort key in rank() and compare it with leaderboard rules 4 and 5.
3. **Exact:** Add s.best_at between the score and the team id.

## "Why did that fix work?" probes

**B1**
- Why are 82.5 and 85.0 exact even with the old code?
- Why did the leaderboard order not change even though the scores were off?

**B2**
- Why didn't this affect T07, whose submissions were all rejected?
- Why are best scores unaffected?

**B3**
- When did T03 and T04 each reach their best score, and which submission counts for each?
- Would the old key ever give the right answer for a tie? When?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `podium/scoring.py` → `pick_best`: Using min() to find the best looks backwards, but the key negates the score, so the smallest key is the highest score, and ties go to the earliest submitted_at, exactly as rule 2 says.
