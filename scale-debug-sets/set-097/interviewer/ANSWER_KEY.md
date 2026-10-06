# set-097 answer key: Hour-capped pod staffing with course recency

**Domain:** contributor_assignment  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_assignment.TestAssignment.test_chat_safety` | B1 Only the first required course is checked |
| `test_1_assignment.TestAssignment.test_spanish_qa` | B2 Rating 0 replaced by the default |
| `test_2_report.TestReport.test_multi_project_contributors` | B3 Project list shared by every contributor |

## Failing pattern with all bugs present

- `tests.test_1_assignment.TestAssignment.test_chat_safety`
- `tests.test_1_assignment.TestAssignment.test_spanish_qa`
- `tests.test_2_report.TestReport.test_multi_project_contributors`

## Bugs (recommended order)

### B1: Only the first required course is checked

- **Type:** early-return
- **Symptom:** Test 1 test_chat_safety: P02 gets ['C01', 'C04'] instead of ['C01', 'C10']. Every other project is unchanged.
- **Location:** `podstaff/rules.py` → `missing_course`
- **Why it fails:** `return None` sits inside the for loop, so missing_course returns after looking at the first course only. C04 has core-101 but their latest safety-201 attempt is a fail, and they become eligible for P02 and outrank C10 on rating. P08 is unaffected because it lists pii-110 first, and nobody without core-101 holds pii-110.
- **Failing test:** `test_1_assignment.TestAssignment.test_chat_safety`
- **Unblocks:** test_1_assignment.TestAssignment.test_chat_safety

Fix:

```diff
             return course
-        return None
+    return None
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_chat_safety`):

```
AssertionError: Lists differ: ['C01', 'C04'] != ['C01', 'C10']

First differing element 1:
'C04'
'C10'

- ['C01', 'C04']
?            -

+ ['C01', 'C10']
?           +
```

### B2: Rating 0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 1 test_spanish_qa: P05 gets ['C03', 'C05'] instead of ['C03', 'C16'].
- **Location:** `podstaff/loader.py` → `load_contributors`
- **Why it fails:** `rating or DEFAULT_RATING` treats C05's real rating of 0 as missing and gives them 3.0, which ranks them above C16 (2.8) and C09 (2.5). Only a blank cell should get the default.
- **Failing test:** `test_1_assignment.TestAssignment.test_spanish_qa`
- **Unblocks:** test_1_assignment.TestAssignment.test_spanish_qa

Fix:

```diff
-                rating=rating or DEFAULT_RATING,
+                rating=DEFAULT_RATING if rating is None else rating,
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_spanish_qa`):

```
AssertionError: Lists differ: ['C03', 'C05'] != ['C03', 'C16']

First differing element 1:
'C05'
'C16'

- ['C03', 'C05']
?           ^^

+ ['C03', 'C16']
?           ^^
```

### B3: Project list shared by every contributor

- **Type:** shared-class-attribute
- **Symptom:** Test 2 test_multi_project_contributors: all 16 contributors appear, inactive and unstaffed ones included, each with the same long list of every pick made so far (it keeps growing with each build_report call in the test run). The assignments themselves are correct.
- **Location:** `podstaff/models.py` → `Contributor`
- **Why it fails:** `projects = []` is a class attribute, so every Contributor's `self.projects.append(...)` writes into one shared list. Hours are tracked per instance, so staffing still works and only the report built from `projects` is affected.
- **Failing test:** `test_2_report.TestReport.test_multi_project_contributors`
- **Unblocks:** test_2_report.TestReport.test_multi_project_contributors

Fix:

```diff
     """One row of contributors.csv plus the running state of a staffing pass."""
-
-    projects = []
 
     def __init__(self, cid, name, locale, weekly_hours, rating, active, joined):
         self.hours_left = weekly_hours
         self.courses = {}
+        self.projects = []
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_multi_project_contributors`):

```
AssertionError: {'C01': ['P01', 'P01', 'P01', 'P01', 'P01', 'P01', 'P02', 'P[4111 chars]10']} != {'C01': ['P01', 'P02', 'P03'], 'C02': ['P01', 'P03'], 'C03':[64 chars]10']}
Diff is 10555 characters long. Set self.maxDiff to None to see it.
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `podstaff/rules.py` → `latest_results`: The `>=` looks like it should be `>`, but rule 1 says that on equal dates the attempt further down the file counts, so a later row with the same date must replace the earlier one. C15's code-301 fail/pass on 2026-02-01 depends on it: with `>` C15 would lose P07 and P10.
- `podstaff/rules.py` → `rank_key`: Negating the rating gives highest-first inside an ascending sort, `date.max` puts blank join dates last, and the id is the final tie-break: exactly rule 5. It looks like it could invert the order, but it doesn't.
