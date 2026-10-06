# set-001 answer key: Contributor staffing by priority with course gates

**Domain:** contributor_assignment  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_assignment.TestAssignment.test_full_assignment_table`
- `tests.test_1_assignment.TestAssignment.test_highest_priority_project_staffed_first`
- `tests.test_2_staffing_report.TestStaffingReport.test_bench`
- `tests.test_2_staffing_report.TestStaffingReport.test_course_gated_projects_fully_staffed`
- `tests.test_2_staffing_report.TestStaffingReport.test_open_seats`

## Bugs (recommended order)

### B1: Projects processed least-important first

- **Type:** sort-direction
- **Symptom:** Test 1: P02 (priority 1) comes back empty. The lowest-priority projects are staffed first (P08 gets C01, P09 gets C03 and C10), so the course-gated P01-P03 run out of eligible people. Test 2 open seats point at P01-P03.
- **Location:** `staffing/assigner.py` → `project_order`
- **Why it fails:** Priority 1 is the most important, so the sort has to be ascending. Negating the key makes the largest number come first. The comment 'most important first' describes the goal, not what the code does.
- **Unblocks:** Test 1 (priority order). Some Test 2 values also recover.

Fix:

```diff
-    return sorted(projects, key=lambda p: (-p.priority, p.id))
+    return sorted(projects, key=lambda p: (p.priority, p.id))
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_full_assignment_table`):

```
AssertionError: {'P01': [], 'P02': [], 'P03': [], 'P04': ['C13', '[120 chars]06']} != {'P01': ['C01', 'C15'], 'P02': ['C06', 'C07'], 'P0[132 chars]: []}
- {'P01': [],
-  'P02': [],
-  'P03': [],
+ {'P01': ['C01', 'C15'],
+  'P02': ['C06', 'C07'],
+  'P03': ['C03', 'C10'],
   'P04': ['C13', 'C09'],
   'P05': [],
-  'P06': ['C07', 'C05', 'C14'],
?          -------

+  'P06': ['C05', 'C14', 'C11'],
? ...
```

### B2: Course requirement checked against skills

- **Type:** wrong-field
- **Symptom:** Test 2: the course-gated projects P01, P02 and P03 get 0 people each. Test 1 also shows them as empty, and the people they should have had end up on later projects.
- **Location:** `staffing/rules.py` → `is_eligible`
- **Why it fails:** The course check looks the course id up in contributor.skills, which never holds course ids. Every course-gated project therefore rejects everyone.
- **Unblocks:** Test 2 course-gated check, but only partly: B3 shows up next.

Fix:

```diff
-    if project.required_course and project.required_course not in contributor.skills:
+    if project.required_course and project.required_course not in contributor.completed_courses:
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_full_assignment_table`):

```
AssertionError: {'P01': [], 'P02': [], 'P03': [], 'P04': ['C01', '[120 chars]09']} != {'P01': ['C01', 'C15'], 'P02': ['C06', 'C07'], 'P0[132 chars]: []}
- {'P01': [],
-  'P02': [],
-  'P03': [],
+ {'P01': ['C01', 'C15'],
+  'P02': ['C06', 'C07'],
+  'P03': ['C03', 'C10'],
-  'P04': ['C01', 'C03'],
?            -       ^

+  'P04': ['C13', 'C09'],
?             +      ^

   'P05': [],
-  'P06': ['C ...
```

### B3: Completed course ids not upper-cased

- **Type:** id-normalization
- **Symptom:** Only visible once B2 is fixed. P01 gets C09 instead of C15, P02 gets C14 instead of C07, and P03 gets only C03 (C10 is missing). Everyone who typed the course in lower case is skipped. Test 2: P03 has 1 open seat and the bench comes back empty.
- **Location:** `staffing/loader.py` → `load_contributors`
- **Why it fails:** Project course ids are upper-cased, but the contributor's completed courses are kept as typed. 'ml-101' is not equal to 'ML-101', so the membership test fails for those contributors.
- **Unblocks:** Tests 1 and 2 fully.
- **Masked:** invisible until B2 is fixed (identical test output either way).

Fix:

```diff
-                completed_courses=set(_split(row["completed_courses"])),
+                completed_courses={c.upper() for c in _split(row["completed_courses"])},
```

Observed with only this bug applied (`tests.test_1_assignment.TestAssignment.test_full_assignment_table`):

```
AssertionError: {'P01': ['C01', 'C09'], 'P02': ['C06', 'C14'], 'P03': ['C03[128 chars]: []} != {'P01': ['C01', 'C15'], 'P02': ['C06', 'C07'], 'P03': ['C03[123 chars]: []}
- {'P01': ['C01', 'C09'],
?                   ^^

+ {'P01': ['C01', 'C15'],
?                   ^^

-  'P02': ['C06', 'C14'],
?                   ^^

+  'P02': ['C06', 'C07'],
?                   ^^

-  'P03': ['C03'],
+  'P03':  ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `staffing/rules.py` → `rank_candidates`: Negating the rating is how you sort highest-first while keeping the joined date and id ascending. It looks just like the broken project sort, but here 'larger is better' really is the rule.
- `staffing/loader.py` → `parse_date`: It tries the three formats the README lists. %m/%d/%Y is month-first, which is what the spec says.
