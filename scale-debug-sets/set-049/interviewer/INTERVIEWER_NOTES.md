# set-049 interviewer notes

**Scenario:** Open projects are staffed highest priority number first; each seat goes to the eligible contributor with the best skill level, then most hours left. The report lists unfilled seats, skill gaps over open projects, and utilisation.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Status check always truthy

1. **Nudge:** E-03 is staffed. Check E-03's status.
2. **Area:** Look at how is_available decides eligibility.
3. **Exact:** `status == 'active' or 'trial'` is always truthy; use `status in ELIGIBLE_STATUSES`.

### B2: skill_level gives up after the first skill

1. **Nudge:** P-01 has sql:9 but wasn't staffed on PR-03. What is different about how P-01's skills are written?
2. **Area:** Trace skill_level for P-01 and 'sql'.
3. **Exact:** The `return 0` is indented inside the for loop; dedent it so it runs after the loop.

### B3: Skill gaps count on-hold projects

1. **Nudge:** Spanish shows 3 missing seats but every open spanish seat is filled. Where do 3 seats come from?
2. **Area:** Which projects does skill_gaps loop over?
3. **Exact:** Loop over project_order(projects) (open projects only), not every project.

## "Why did that fix work?" probes

**B1**
- Why didn't offboarded A-04 show up in any assignment?
- What does `bool('active' == 'paused' or 'trial')` evaluate to, and why?

**B2**
- Why were the Americas projects unaffected even though A-01 and A-05 also list two skills?
- How would you write a test that catches this directly?

**B3**
- Why doesn't the `unfilled` section show PR-07 even though skill_gaps counts it?
- Why did this not raise a KeyError for on-hold projects?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `seatplan/assigner.py` → `project_order`: Sorting by `-p.priority` looks like a flipped sort, but this README says the higher number is more important, so descending is right; ties go to the lower id and only open projects are kept.
