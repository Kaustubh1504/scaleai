# set-073 answer key: Hours-capped crew planner with expiring certifications

**Domain:** contributor_assignment  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_staffing.TestStaffing.test_assignments` | B1 Paused check compares an Enum to a string |
| `test_2_courses.TestCourseCoverage.test_course_holders` | B2 Holder sets shared by every course |
| `test_2_courses.TestCourseCoverage.test_most_demanded` | B3 Demand counts paused projects |

## Failing pattern with all bugs present

- `tests.test_1_staffing.TestStaffing.test_assignments`
- `tests.test_2_courses.TestCourseCoverage.test_course_holders`
- `tests.test_2_courses.TestCourseCoverage.test_most_demanded`

## Bugs (recommended order)

### B1: Paused check compares an Enum to a string

- **Type:** enum-vs-string
- **Symptom:** Test 1 test_assignments: the paused projects get teams (P06 ['K13', 'K11'], P07 ['K08'], P12 ['K08']). Every open project's team is exactly as expected, and open_seats is unchanged.
- **Location:** `crewplan/scheduler.py` → `staff`
- **Why it fails:** project.status is a Status member, and a plain Enum member never equals its value string, so the check is always False and paused projects are staffed. They are the lowest priority, so they only take leftover hours and every open project is unchanged.
- **Failing test:** `test_1_staffing.TestStaffing.test_assignments`
- **Unblocks:** test_assignments.

Fix:

```diff
# crewplan/scheduler.py
-        if project.status == "paused":
+        if project.status == Status.PAUSED:

# crewplan/scheduler.py
+from .models import Status
```

Observed with only this bug applied (`tests.test_1_staffing.TestStaffing.test_assignments`):

```
AssertionError: {'P01[107 chars]6': ['K13', 'K11'], 'P07': ['K08'], 'P08': ['K[73 chars]08']} != {'P01[107 chars]6': [], 'P07': [], 'P08': ['K01'], 'P09': ['K1[51 chars]: []}
  {'P01': ['K02', 'K03'],
   'P02': ['K04'],
   'P03': ['K09', 'K13'],
   'P04': ['K13', 'K03', 'K07'],
   'P05': ['K06'],
-  'P06': ['K13', 'K11'],
+  'P06': [],
-  'P07': ['K08'],
?          -----

+  'P07': [],
   'P08': [ ...
```

### B2: Holder sets shared by every course

- **Type:** shared-class-attribute
- **Symptom:** Test 2 test_course_holders: every course shows 13 holders ({'CODE-300': 13, 'LANG-ES': 13, 'MED-200': 13, 'QA-101': 13}) instead of 4/3/6/9.
- **Location:** `crewplan/models.py` → `CourseStats.__init__`
- **Why it fails:** A set defined at class level is one object shared by every CourseStats instance, and .add() mutates it in place, so every course reports the union of all holders. `demand = 0` is fine at class level because `+= 1` on an int rebinds an instance attribute.
- **Failing test:** `test_2_courses.TestCourseCoverage.test_course_holders`
- **Unblocks:** test_course_holders.

Fix:

```diff
     demand = 0
-    holders = set()
 
     def __init__(self, course_id):
+        self.holders = set()
```

Observed with only this bug applied (`tests.test_2_courses.TestCourseCoverage.test_course_holders`):

```
AssertionError: {'CODE-300': 13, 'LANG-ES': 13, 'MED-200': 13, 'QA-101': 13} != {'CODE-300': 4, 'LANG-ES': 3, 'MED-200': 6, 'QA-101': 9}
- {'CODE-300': 13, 'LANG-ES': 13, 'MED-200': 13, 'QA-101': 13}
?              ^^             -              ^^            ^^

+ {'CODE-300': 4, 'LANG-ES': 3, 'MED-200': 6, 'QA-101': 9}
?              ^                           ^            ^
```

### B3: Demand counts paused projects

- **Type:** counting-wrong-subset
- **Symptom:** Test 2 test_most_demanded: 'MED-200' instead of 'QA-101'.
- **Location:** `crewplan/reports.py` → `course_table`
- **Why it fails:** Demand should count only open projects. Counting all of them adds the three paused MED-200 projects, so MED-200 ties QA-101 at 5 and wins the tie on course id.
- **Failing test:** `test_2_courses.TestCourseCoverage.test_most_demanded`
- **Unblocks:** test_most_demanded.

Fix:

```diff
# crewplan/reports.py
-            entry.demand += 1
+            if project.status is Status.OPEN:
+                entry.demand += 1

# crewplan/reports.py
-from .models import CourseStats
+from .models import CourseStats, Status
```

Observed with only this bug applied (`tests.test_2_courses.TestCourseCoverage.test_most_demanded`):

```
AssertionError: 'MED-200' != 'QA-101'
- MED-200
+ QA-101
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `crewplan/eligibility.py` → `is_current`: `.days` looks like the classic timedelta trap, but the operands are dates, so `.days` is the whole difference. The chained `0 <= ... <= valid_days` rejects future completions (K10's QA-101) and keeps K01's MED-200, completed exactly 365 days before as_of.
- `crewplan/scheduler.py` → `rank_candidates`: The negated sort key looks like a sort-direction slip, but `-rating` then `-hours_left` then `id` is exactly rule 5: highest rating, then more remaining hours, then the lower id.
