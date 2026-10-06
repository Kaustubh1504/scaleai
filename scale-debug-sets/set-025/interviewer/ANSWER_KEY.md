# set-025 answer key: Weekly hours split across projects by score and region

**Domain:** contributor_assignment  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_allocations.TestAllocations.test_all_allocations`
- `tests.test_1_allocations.TestAllocations.test_unfilled`
- `tests.test_2_capacity_report.TestCapacityReport.test_idle`
- `tests.test_2_capacity_report.TestCapacityReport.test_utilization`

## Bugs (recommended order)

### B1: Best score taken over the raw strings

- **Type:** string-vs-int
- **Symptom:** Test 1: test_all_allocations shows P06 going to C03 (10) instead of C05, then P05 becomes {C09: 10, C11: 5} and P10 gives C05 9 hours. Test 2: C05 utilization 0.36 instead of 0.56, C11 0.5 instead of 0.0, and idle is [] instead of ['C11'].
- **Location:** `crew/loader.py` → `best_scores`
- **Why it fails:** max() over strings compares them alphabetically, so '79' beats '100' and C05's audio score becomes 79. C05 drops behind C03 for P06, which shifts hours on P05 and P10.
- **Unblocks:** test_all_allocations, test_utilization (and exposes B2).

Fix:

```diff
-        cid: {skill: int(max(scores)) for skill, scores in skills.items()}
+        cid: {skill: max(int(s) for s in scores) for skill, scores in skills.items()}
```

Observed with only this bug applied (`tests.test_1_allocations.TestAllocations.test_all_allocations`):

```
AssertionError: {'P01[114 chars] {'C09': 10, 'C11': 5}, 'P06': {'C03': 10}, 'P[62 chars]: 9}} != {'P01[114 chars] {'C03': 10, 'C09': 5}, 'P06': {'C05': 10}, 'P[72 chars]: 4}}
  {'P01': {'C01': 20, 'C08': 8, 'C12': 2},
   'P02': {'C04': 14, 'C10': 6},
   'P03': {'C02': 10, 'C03': 10},
   'P04': {},
-  'P05': {'C09': 10, 'C11': 5},
+  'P05': {'C03': 10, 'C09': 5},
-  'P06': {'C03': 10},
?            ...
```

### B2: Region check reads as `x == y or "any"`

- **Type:** or-precedence
- **Symptom:** Only visible after B1 is fixed. Test 1: P03 (EMEA only) goes entirely to C05 (apac) {C05: 20} instead of {C02: 10, C03: 10}; P05 and P06 shift as a result. Test 2: C03 0.75, C05 1.0, C09 0.4 utilization.
- **Location:** `crew/rules.py` → `region_ok`
- **Why it fails:** `a == b or "any"` is `(a == b) or "any"`, and a non-empty string is truthy, so every contributor passes the region gate. C05 (apac, audio 100) takes all 20 hours of the EMEA-only P03.
- **Unblocks:** test_top_priority_projects, test_all_allocations and test_utilization.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-    return contributor.region == project.region or "any"
+    return project.region == "any" or contributor.region == project.region
```

Observed with only this bug applied (`tests.test_1_allocations.TestAllocations.test_all_allocations`):

```
AssertionError: {'P01[72 chars] {'C05': 20}, 'P04': {}, 'P05': {'C03': 15}, '[102 chars]: 4}} != {'P01[72 chars] {'C02': 10, 'C03': 10}, 'P04': {}, 'P05': {'C[114 chars]: 4}}
  {'P01': {'C01': 20, 'C08': 8, 'C12': 2},
   'P02': {'C04': 14, 'C10': 6},
-  'P03': {'C05': 20},
+  'P03': {'C02': 10, 'C03': 10},
   'P04': {},
-  'P05': {'C03': 15},
-  'P06': {'C02': 5, 'C05': 5},
?     ^       ^   ^     ...
```

### B3: Allocation stops at the first contributor with no hours left

- **Type:** early-return
- **Symptom:** Test 1: P05, P08 and P10 get no hours; unfilled becomes {P04: 10, P05: 15, P08: 10, P09: 8, P10: 12}. Test 2: idle is ['C09', 'C11'] and utilization drops for C03, C04, C05, C09 and C12.
- **Location:** `crew/allocator.py` → `allocate`
- **Why it fails:** Rule 5 skips a contributor with no hours left. `break` ends the whole project instead, so any project whose top candidate is used up gets nothing: P08 (C10), P05 (C10) and P10 (C08), even though C04, C03, C09, C12 and C05 still had hours.
- **Unblocks:** test_all_allocations, test_unfilled, test_utilization and test_idle.

Fix:

```diff
             if remaining[cand.id] == 0:
-                break
+                continue
```

Observed with only this bug applied (`tests.test_1_allocations.TestAllocations.test_all_allocations`):

```
AssertionError: {'P01[111 chars]5': {}, 'P06': {'C05': 10}, 'P07': {}, 'P08': [20 chars]: {}} != {'P01[111 chars]5': {'C03': 10, 'C09': 5}, 'P06': {'C05': 10},[75 chars]: 4}}
  {'P01': {'C01': 20, 'C08': 8, 'C12': 2},
   'P02': {'C04': 14, 'C10': 6},
   'P03': {'C02': 10, 'C03': 10},
   'P04': {},
-  'P05': {},
+  'P05': {'C03': 10, 'C09': 5},
   'P06': {'C05': 10},
   'P07': {},
-  'P08': {},
+   ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `crew/allocator.py` → `candidate_order`: Sorting on negated score and negated remaining hours gives highest score first and, on ties, most remaining hours first, with id ascending last, exactly rule 5. It is called before any hours are taken for the project, so `remaining` is the right snapshot.
