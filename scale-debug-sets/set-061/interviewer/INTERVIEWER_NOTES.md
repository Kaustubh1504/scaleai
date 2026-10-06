# set-061 interviewer notes

**Scenario:** Scan one batch of ticket-summary submissions for rushing (duration below 25% of the task median) and copying (same normalised answer as another annotator on the same task), then flag annotators and pick the worst rusher.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Rush rate floored by integer division

1. **Nudge:** Only A02's rate is off, and only in the decimals. What is special about 1 of 3?
2. **Area:** Look at how rush_rate is computed in timing.py.
3. **Exact:** `100 * rushed // timed` floors; use `/` so round(..., 1) has a fraction to round.

### B2: Own submission ends the twin search

1. **Nudge:** A04 and A08 share four answers, yet each gets credit for only two. Which two, in file order?
2. **Area:** Look at what has_twin does when it reaches a submission by the same annotator.
3. **Exact:** The own-annotator check returns False; it should `continue` to the next submission.

### B3: Worst-rusher tie goes to first seen

1. **Nudge:** Two annotators share the highest rush rate. Which one does the spec want?
2. **Area:** Look at how worst_rusher picks between equal rates, and what order its input is in.
3. **Exact:** Use min(timed, key=lambda a: (-timed[a]["rush_rate"], a)).

## "Why did that fix work?" probes

**B1**
- Why did A03 and A05 (2 of 4) come out right with the floor?
- Why is the `//` in median() fine while this one isn't?

**B2**
- Why did A04 lose t1 and t2 but keep t3 and t4?
- Why didn't the copying flags change even though the counts did?

**B3**
- Would this have passed if worst_rusher were given the `rows` dict instead of `rush`? Why?
- What does max() do with equal keys?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `tripwire/timing.py` → `median`: The `//` only computes the middle index, which must be an integer. The even case divides the sum of the two middle values with `/`, so t2 correctly gives 112.5. It looks like the integer-division suspect but it is fine.
