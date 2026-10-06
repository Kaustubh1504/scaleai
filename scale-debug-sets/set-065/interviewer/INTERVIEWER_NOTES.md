# set-065 interviewer notes

**Scenario:** Build a public benchmark leaderboard: best score per team and task up to an inclusive freeze, mean over three tasks (missing = 0), competition ranking (1,2,3,3,5) and a top-3 podium per division.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Best score picked by string comparison

1. **Nudge:** basalt scored 100 on gsm8k, but its best shows 98.5. What type are the values being compared?
2. **Area:** Look at how best_per_task decides that a new submission beats the current one.
3. **Exact:** Compare float(s.score) > float(current.score).

### B2: Resubmissions counted as extra tasks

1. **Nudge:** aurora shows 4 tasks attempted on a three-task benchmark.
2. **Area:** Look at how tasks_attempted collects tasks per team.
3. **Exact:** Collect into a set (defaultdict(set) and .add) so repeats collapse.

### B3: Submission at the freeze dropped

1. **Nudge:** One mmlu submission is missing from the counts. Look for rows near the freeze time.
2. **Area:** Check the freeze comparison in the loader against rule 3.
3. **Exact:** Use `submitted > FREEZE` so the 23:59 row is kept.

## "Why did that fix work?" probes

**B1**
- Why did every other team's best come out right with the text comparison?
- Why didn't the ranking test fail even though basalt's score dropped?

**B2**
- Which teams were affected, and what do they have in common?
- Would counting the keys of best_per_task's result give the same answer? Why?

**B3**
- Why didn't s-koi's score or rank change?
- What data would make this boundary change the leaderboard itself?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `podium/ranking.py` → `competition_ranks`: Comparing each row with the previous one and reusing the previous rank gives shared ranks for ties, and `i + 1` for the next distinct score skips the right number of places (aurora and cobalt are both 3, s-iris is 5). It looks as if it should count distinct scores, but that would be dense ranking, which the spec does not ask for.
