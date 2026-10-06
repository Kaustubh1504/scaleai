# set-001 interviewer notes

**Scenario:** Assign contributors to projects in priority order (1 = most important). Some projects require a completed course. Each contributor works on one project; best-rated eligible people are picked first.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Projects processed least-important first

1. **Nudge:** Look at which projects got staffed first. Does that match the README?
2. **Area:** Check how assigner.py orders the projects.
3. **Exact:** project_order negates priority. Priority 1 must come first, so sort ascending: key=(p.priority, p.id).

### B2: Course requirement checked against skills

1. **Nudge:** Which projects come back empty? What do they have in common?
2. **Area:** Look at the eligibility rules in rules.py.
3. **Exact:** is_eligible compares required_course against contributor.skills. It should compare against contributor.completed_courses.

### B3: Completed course ids not upper-cased

1. **Nudge:** Compare the people who still miss out with the ones who get in. Look at how their courses are spelled in the CSV.
2. **Area:** Compare how loader.py cleans project course ids with how it cleans contributor course ids.
3. **Exact:** load_contributors stores completed_courses without .upper(). Use {c.upper() for c in _split(...)}.

## "Why did that fix work?" probes

**B1**
- If the data's convention changed to 'higher number = more important', what would you change, and would the tie-break on id still be right?
- rank_candidates also negates a field. Why is it correct there and not here?

**B2**
- Why didn't this raise an error, even though a course id is never a skill?
- After the fix, why do C03, C07 and C10 still miss out? (This leads to B3.)

**B3**
- Why was this invisible until the skills/courses mix-up was fixed?
- Where else in the loader could the same case mismatch happen, and why doesn't it?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `staffing/rules.py` → `rank_candidates`: Negating the rating is how you sort highest-first while keeping the joined date and id ascending. It looks just like the broken project sort, but here 'larger is better' really is the rule.
- `staffing/loader.py` → `parse_date`: It tries the three formats the README lists. %m/%d/%Y is month-first, which is what the spec says.
