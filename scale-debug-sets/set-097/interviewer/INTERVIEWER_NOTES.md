# set-097 interviewer notes

**Scenario:** Staff ten projects by descending priority number. Contributors can take several projects while weekly hours last; eligibility needs locale, hours, and every listed course passed on the most recent attempt. The report lists multi-project contributors and course demand.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Only the first required course is checked

1. **Nudge:** Look up C04 in courses.csv. Which P02 course do they hold right now?
2. **Area:** Look at how missing_course walks the project's course list.
3. **Exact:** The `return None` is indented into the loop; dedent it so every course is checked.

### B2: Rating 0 replaced by the default

1. **Nudge:** C05 is on probation with a rating of 0. Why would they be picked ahead of C16?
2. **Area:** Look at how the loader applies the default rating.
3. **Exact:** `rating or DEFAULT_RATING` turns 0.0 into 3.0; use `DEFAULT_RATING if rating is None else rating`.

### B3: Project list shared by every contributor

1. **Nudge:** Even C07, who is inactive, shows up in multi_project. Where does that list come from?
2. **Area:** Look at where a Contributor's `projects` list is created.
3. **Exact:** Remove the class-level `projects = []` and set `self.projects = []` in __init__.

## "Why did that fix work?" probes

**B1**
- P08 also lists two courses. Why did it come out right with the early return in place?
- C04 is free again after the fix. Why doesn't that change any later project?

**B2**
- Why did C11 (blank rating) behave the same before and after the fix?
- Why didn't C16 losing P05 change P09 or P10?

**B3**
- Why did hours_left keep working per contributor when projects didn't?
- Why would the list have grown even further if build_report ran twice in one process?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `podstaff/rules.py` → `latest_results`: The `>=` looks like it should be `>`, but rule 1 says that on equal dates the attempt further down the file counts, so a later row with the same date must replace the earlier one. C15's code-301 fail/pass on 2026-02-01 depends on it: with `>` C15 would lose P07 and P10.
- `podstaff/rules.py` → `rank_key`: Negating the rating gives highest-first inside an ascending sort, `date.max` puts blank join dates last, and the id is the final tie-break: exactly rule 5. It looks like it could invert the order, but it doesn't.
