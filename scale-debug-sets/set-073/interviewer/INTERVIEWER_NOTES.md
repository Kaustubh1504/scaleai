# set-073 interviewer notes

**Scenario:** Fill project seats in priority order (higher number = more important) from contributors with weekly hour budgets and current course certifications, then build a course coverage table (holders, open-project demand, most demanded course).

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Paused check compares an Enum to a string

1. **Nudge:** The paused projects have teams. Does the scheduler know they are paused?
2. **Area:** Print project.status and what the skip check compares it to.
3. **Exact:** Compare with Status.PAUSED (or `is Status.PAUSED`), not the string "paused".

### B2: Holder sets shared by every course

1. **Nudge:** Every course has the same holder count. What would make four courses see the same set?
2. **Area:** Look at where CourseStats gets its holders set.
3. **Exact:** Create the set per instance in __init__: self.holders = set().

### B3: Demand counts paused projects

1. **Nudge:** Compute demand per course by hand from projects.csv. Which projects did you count?
2. **Area:** Look at which projects course_table adds to demand.
3. **Exact:** Only count a requirement when project.status is Status.OPEN.

## "Why did that fix work?" probes

**B1**
- Would the comparison work if Status subclassed str? Why?
- Why did no open project's team change with this bug present?

**B2**
- Why doesn't `demand = 0` at class level have the same problem?
- Why is 13 (and not 14) the number every course shows?

**B3**
- Why does MED-200 win rather than tie in the output?
- Which other report field would show this bug directly?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `crewplan/eligibility.py` → `is_current`: `.days` looks like the classic timedelta trap, but the operands are dates, so `.days` is the whole difference. The chained `0 <= ... <= valid_days` rejects future completions (K10's QA-101) and keeps K01's MED-200, completed exactly 365 days before as_of.
- `crewplan/scheduler.py` → `rank_candidates`: The negated sort key looks like a sort-direction slip, but `-rating` then `-hours_left` then `id` is exactly rule 5: highest rating, then more remaining hours, then the lower id.
