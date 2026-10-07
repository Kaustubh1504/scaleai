# set-049 answer key: Weekly seat planner with skill levels and hour budgets

**Domain:** contributor_assignment  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_assignment.TestAssignment.test_1_emea_projects` | B1 Status check always truthy |
| `test_1_assignment.TestAssignment.test_2_apac_projects` | B2 skill_level gives up after the first skill |
| `test_2_report.TestReport.test_3_skill_gaps_for_americas_skills` | B3 Skill gaps count on-hold projects |

## Failing pattern with all bugs present

- `tests.test_1_assignment.TestAssignment.test_1_emea_projects`
- `tests.test_1_assignment.TestAssignment.test_2_apac_projects`
- `tests.test_2_report.TestReport.test_3_skill_gaps_for_americas_skills`

## Bugs (recommended order)

### B1: Status check always truthy

- **Type:** or-precedence
- **Symptom:** Test 1 test_1_emea_projects: PR-01 is ['E-03', 'E-01', 'E-02'] and PR-02 is ['E-03', 'E-01'] instead of ['E-01', 'E-02'] for both. The paused E-03 is staffed.
- **Location:** `seatplan/rules.py` → `is_available`
- **Why it fails:** This parses as `(status == 'active') or 'trial'`, and the non-empty string 'trial' is truthy, so every status passes. Paused E-03 (python 9) takes the top seat on PR-01 and PR-02.
- **Failing test:** `test_1_assignment.TestAssignment.test_1_emea_projects`
- **Unblocks:** test_1_emea_projects

Fix:

```diff
-    return contributor.status == "active" or "trial"
+    return contributor.status in ELIGIBLE_STATUSES
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_1_emea_projects`):

```
AssertionError: {'PR-01': ['E-03', 'E-01', 'E-02'], 'PR-02': ['E-03', 'E-01']} != {'PR-01': ['E-01', 'E-02'], 'PR-02': ['E-01', 'E-02']}
- {'PR-01': ['E-03', 'E-01', 'E-02'], 'PR-02': ['E-03', 'E-01']}
?            --------                           --------

+ {'PR-01': ['E-01', 'E-02'], 'PR-02': ['E-01', 'E-02']}
?                                             ++++++++
```

### B2: skill_level gives up after the first skill

- **Type:** early-return
- **Symptom:** Test 1 test_2_apac_projects: PR-03 is ['P-02', 'P-03'] instead of ['P-01', 'P-02']. P-01's sql:9 is not seen.
- **Location:** `seatplan/rules.py` → `skill_level`
- **Why it fails:** With `return 0` inside the loop, only a contributor's first listed skill is ever checked. P-01 lists python before sql, so their sql level 9 reads as 0 and P-03 takes the seat instead.
- **Failing test:** `test_1_assignment.TestAssignment.test_2_apac_projects`
- **Unblocks:** test_2_apac_projects

Fix:

```diff
             return level
-        return 0
+    return 0
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_2_apac_projects`):

```
AssertionError: Lists differ: ['P-02', 'P-03'] != ['P-01', 'P-02']

First differing element 0:
'P-02'
'P-01'

- ['P-02', 'P-03']
+ ['P-01', 'P-02']
```

### B3: Skill gaps count on-hold projects

- **Type:** counting-wrong-subset
- **Symptom:** Test 2 test_3_skill_gaps_for_americas_skills: spanish shows 3 unfilled seats instead of 0 (math is still 1).
- **Location:** `seatplan/reports.py` → `skill_gaps`
- **Why it fails:** `unfilled` is computed for every project, including on-hold ones that are never staffed, so iterating all projects adds PR-07's three spanish seats (and PR-09/PR-10) to the gaps. The spec counts open projects only.
- **Failing test:** `test_2_report.TestReport.test_3_skill_gaps_for_americas_skills`
- **Unblocks:** test_3_skill_gaps_for_americas_skills

Fix:

```diff
# seatplan/reports.py
-    for project in projects:
+    for project in project_order(projects):

# seatplan/reports.py
-from .assigner import staff
+from .assigner import project_order, staff
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_3_skill_gaps_for_americas_skills`):

```
AssertionError: {'math': 1, 'spanish': 3} != {'math': 1, 'spanish': 0}
- {'math': 1, 'spanish': 3}
?                        ^

+ {'math': 1, 'spanish': 0}
?                        ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `seatplan/assigner.py` → `project_order`: Sorting by `-p.priority` looks like a flipped sort, but this README says the higher number is more important, so descending is right; ties go to the lower id and only open projects are kept.
