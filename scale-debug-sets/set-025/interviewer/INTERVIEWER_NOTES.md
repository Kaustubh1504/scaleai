# set-025 interviewer notes

**Scenario:** Fill projects in priority order (higher number = more important) with hours from contributors who pass the skill score and region gates, highest score first, splitting each contributor's weekly hours across projects. Test 2 reports utilization and idle contributors.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Best score taken over the raw strings

1. **Nudge:** C05 scored 100 in audio. Why is C03 first on P06?
2. **Area:** Look at how a contributor's best attempt is chosen.
3. **Exact:** Convert before taking the max: max(int(s) for s in scores).

### B2: Region check reads as `x == y or "any"`

1. **Nudge:** P03 is EMEA-only. Which region is the contributor it went to in?
2. **Area:** Look at the region rule in rules.py and how Python groups `or`.
3. **Exact:** region_ok should be project.region == "any" or contributor.region == project.region.

### B3: Allocation stops at the first contributor with no hours left

1. **Nudge:** P05 needs 15 hours and gets none, yet C03 and C09 have hours left. Who is first in its candidate order?
2. **Area:** Look at what happens in allocate when a candidate has no hours left.
3. **Exact:** That check should `continue`, not `break`.

## "Why did that fix work?" probes

**B1**
- Why were all the other contributors' best scores right?
- Why did this hide the region problem on P03?

**B2**
- Why was this invisible while B1 was present?
- What does region_ok return here when the regions differ? Is it a bool?

**B3**
- Why did P04 come out the same with and without the fix?
- How would filtering out exhausted contributors before the loop change things?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `crew/allocator.py` → `candidate_order`: Sorting on negated score and negated remaining hours gives highest score first and, on ties, most remaining hours first, with id ascending last, exactly rule 5. It is called before any hours are taken for the project, so `remaining` is the right snapshot.
