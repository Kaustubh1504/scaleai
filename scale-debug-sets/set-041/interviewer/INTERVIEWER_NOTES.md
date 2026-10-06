# set-041 interviewer notes

**Scenario:** Build an individual sprint leaderboard (best points per task, fewer attempts wins ties, competition ranking) from a messy submission export with duplicate rows, banned and unknown contributors, then rank teams by their two best members.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Loop stops at the first banned contributor

1. **Nudge:** submissions_counted is far below the number of graded rows. Which rows are the last ones that still count?
2. **Area:** Look at how eligible() handles a submission from a banned contributor.
3. **Exact:** eligible() uses `break` for banned/unknown contributors; it should be `continue`.

### B2: Export duplicates never removed

1. **Nudge:** Scores look right, but c-02, c-03 and c-12 have one attempt too many. Look for their rows in submissions.csv.
2. **Area:** The README says rows with the same submission id are the same submission. Where does the loader handle that?
3. **Exact:** load_submissions returns `graded`; it should return `first_per_id(graded)`.

### B3: Team ties ordered reverse-alphabetically

1. **Nudge:** Herons and Otters have the same score. Which should be first by rule 10?
2. **Area:** Look at how team_standings sorts the table.
3. **Exact:** Sort by `(-t["score"], t["team"])` without reverse=True.

## "Why did that fix work?" probes

**B1**
- Why did the out-of-season row S011 not cut the list short, even though it is skipped too?
- Why did the duplicate-row problem stay invisible until this was fixed?

**B2**
- Why didn't the duplicates change anyone's score?
- Why does the dedupe need to run after the ids are upper-cased and trimmed?

**B3**
- Why did reverse=True still get Falcons and Lynx in the right places?
- How else could you sort descending on one key and ascending on another if the key weren't numeric?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `ladder/scoring.py` → `assign_ranks`: `rank = i + 1` looks like it should be `rank += 1`, but standard competition ranking (1, 2, 2, 4) means a new rank is the row's 1-based position, not the previous rank plus one. Rows only share a rank when both score and attempts match, exactly as rule 7 says.
