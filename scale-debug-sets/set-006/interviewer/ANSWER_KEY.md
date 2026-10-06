# set-006 answer key: Review queue replay with rework escalation

**Domain:** review_state_machine  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_lifecycle.TestLifecycle.test_final_states`
- `tests.test_1_lifecycle.TestLifecycle.test_invalid_events`
- `tests.test_1_lifecycle.TestLifecycle.test_rework_and_assignees`
- `tests.test_1_lifecycle.TestLifecycle.test_transition_counts`
- `tests.test_2_people.TestPeople.test_annotator_approvals`
- `tests.test_2_people.TestPeople.test_annotator_submissions`
- `tests.test_2_people.TestPeople.test_reviewer_table`
- `tests.test_3_summary.TestSummary.test_avg_cycle_hours`
- `tests.test_3_summary.TestSummary.test_first_pass_rate`
- `tests.test_3_summary.TestSummary.test_open_by_queue`
- `tests.test_3_summary.TestSummary.test_state_counts`

## Bugs (recommended order)

### B1: History list shared by every task

- **Type:** shared-class-attribute
- **Symptom:** Test 1 test_transition_counts: every task reports 34 transitions (the total number of applied events) instead of 3, 6, 3, 9, ... Nothing else changes.
- **Location:** `reviewflow/models.py` → `TaskRecord.__init__`
- **Why it fails:** `history = []` at class level is a single list object shared by every TaskRecord. `task.history.append(...)` mutates that one list, so every task sees every applied event. The scalar class defaults (state, rework) are safe only because they are reassigned, never mutated.
- **Unblocks:** test_1_lifecycle.test_transition_counts.

Fix:

```diff
     closed_at = None
-    history = []
 
     def __init__(self, task_id, queue, created_at):
         self.queue = queue
         self.created_at = created_at
+        self.history = []
```

Observed with only this bug applied (`tests.test_1_lifecycle.TestLifecycle.test_transition_counts`):

```
AssertionError: {'T01': 34, 'T02': 34, 'T03': 34, 'T04': 34, 'T05'[77 chars]: 34} != {'T01': 3, 'T02': 6, 'T03': 3, 'T04': 9, 'T05': 2,[65 chars]': 0}
- {'T01': 34,
?          -

+ {'T01': 3,
-  'T02': 34,
?         ^^

+  'T02': 6,
?         ^

-  'T03': 34,
?          -

+  'T03': 3,
-  'T04': 34,
?         ^^

+  'T04': 9,
?         ^

-  'T05': 34,
?         ^^

+  'T05': 2,
?         ^

-  'T ...
```

### B2: Same-time events ordered by id string

- **Type:** string-vs-int
- **Symptom:** Test 1: T05 ends 'claimed' instead of 'submitted' with 1 transition, and E12 heads the invalid list. Test 2: ann-02 has 3 submissions instead of 4. Test 3: state_counts shows claimed 2 / submitted 1.
- **Location:** `reviewflow/loader.py` → `load_events`
- **Why it fails:** Event ids are strings, and `"E12" < "E8"` lexicographically. E8 (claim) and E12 (submit) on T05 share a timestamp, so the submit is replayed first against a queued task and rejected.
- **Unblocks:** T05 in test_1_lifecycle, and the invalid list.

Fix:

```diff
-    events.sort(key=lambda ev: (ev.at, ev.event_id))
+    events.sort(key=lambda ev: (ev.at, ev.seq))
```

Observed with only this bug applied (`tests.test_1_lifecycle.TestLifecycle.test_final_states`):

```
AssertionError: {'T01[76 chars]5': 'claimed', 'T06': 'claimed', 'T07': 'queue[90 chars]ued'} != {'T01[76 chars]5': 'submitted', 'T06': 'claimed', 'T07': 'que[92 chars]ued'}
  {'T01': 'approved',
   'T02': 'approved',
   'T03': 'approved',
   'T04': 'escalated',
-  'T05': 'claimed',
+  'T05': 'submitted',
   'T06': 'claimed',
   'T07': 'queued',
   'T08': 'approved',
   'T09': 'queued',
   'T10': ' ...
```

### B3: Review state compared to a string

- **Type:** enum-vs-string
- **Symptom:** Every approve and reject is invalid. Test 1: all reviewed tasks stay 'submitted', T04 never escalates, the invalid list has 21 ids. Test 2: reviewer and annotator approval counts are all 0. Test 3: first_pass_rate and avg_cycle_hours are None, submitted = 8.
- **Location:** `reviewflow/transitions.py` → `_reviewable`
- **Why it fails:** `State` is a plain Enum, so `State.SUBMITTED != "submitted"` is always True. Every approve and reject is treated as invalid and no task ever leaves `submitted`.
- **Unblocks:** Most of test_1 and test_2, and exposes B5 and B6 in test_3.

Fix:

```diff
-    if task.state != "submitted":
+    if task.state is not State.SUBMITTED:
```

Observed with only this bug applied (`tests.test_1_lifecycle.TestLifecycle.test_final_states`):

```
AssertionError: {'T01': 'submitted', 'T02': 'submitted', 'T03': 's[174 chars]ued'} != {'T01': 'approved', 'T02': 'approved', 'T03': 'app[169 chars]ued'}
- {'T01': 'submitted',
-  'T02': 'submitted',
-  'T03': 'submitted',
+ {'T01': 'approved',
+  'T02': 'approved',
+  'T03': 'approved',
-  'T04': 'submitted',
?           ^^^^^

+  'T04': 'escalated',
?          + ^^^^

   'T05': 'submitted',
   'T ...
```

### B4: Any role can review

- **Type:** or-precedence
- **Symptom:** Test 1: E13 is invalid instead of E11 (ann-01's approval of T03 is accepted). Test 2: annotators ann-01..ann-05 appear in the reviewers table and rev-02 has 1 approval instead of 2. Test 3: avg_cycle_hours 24.2 instead of 24.5.
- **Location:** `reviewflow/models.py` → `Member.can_review`
- **Why it fails:** `a == b or "lead"` parses as `(a == b) or "lead"`, which is the truthy string "lead" for every non-reviewer. Annotators pass the review check, so ann-01's approval of T03 (E11) is applied.
- **Unblocks:** test_2_people.test_reviewer_table, and T03's numbers elsewhere.

Fix:

```diff
-        return self.role == "reviewer" or "lead"
+        return self.role == "reviewer" or self.role == "lead"
```

Observed with only this bug applied (`tests.test_1_lifecycle.TestLifecycle.test_invalid_events`):

```
AssertionError: Lists differ: ['E13', 'E17', 'E33', 'E36', 'E40', 'E38'] != ['E11', 'E17', 'E33', 'E36', 'E40', 'E38']

First differing element 0:
'E13'
'E11'

- ['E13', 'E17', 'E33', 'E36', 'E40', 'E38']
?     ^

+ ['E11', 'E17', 'E33', 'E36', 'E40', 'E38']
?     ^
```

### B5: Cycle time ignores whole days

- **Type:** timedelta-seconds
- **Symptom:** Only visible once B3 is fixed. Test 3 test_avg_cycle_hours: 5.3 instead of 24.5.
- **Location:** `reviewflow/metrics.py` → `cycle_hours`
- **Why it fails:** `timedelta.seconds` is only the seconds part after whole days are removed. T02 (50 h) counts as 2 h and T08 (54 h) as 6 h.
- **Unblocks:** test_3_summary.test_avg_cycle_hours.
- **Masked:** invisible until B3 is fixed (identical test output either way).

Fix:

```diff
-    return (task.closed_at - task.created_at).seconds / 3600
+    return (task.closed_at - task.created_at).total_seconds() / 3600
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_avg_cycle_hours`):

```
AssertionError: 5.3 != 24.5
```

### B6: First-pass count taken over all tasks

- **Type:** counting-wrong-subset
- **Symptom:** Only visible once B3 is fixed, and only in Test 3: first_pass_rate is 2.0 instead of 0.8.
- **Location:** `reviewflow/reports.py` → `summarize`
- **Why it fails:** The numerator counts every task with no rework, including queued and claimed ones, while the denominator is approved tasks only, so the rate goes above 1.
- **Unblocks:** test_3_summary.test_first_pass_rate.
- **Masked:** invisible until B3 is fixed (identical test output either way).
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-    first_pass = [t for t in tasks.values() if t.rework == 0]
+    first_pass = [t for t in approved if t.rework == 0]
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_first_pass_rate`):

```
AssertionError: 2.0 != 0.8
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `reviewflow/transitions.py` → `reject`: `rework >= MAX_REWORK` looks like it should be `>`, but the spec escalates when the rework count *reaches* 3, i.e. on the third rejection. T04 is rejected exactly three times and must end escalated.
- `reviewflow/loader.py` → `parse_when`: It tries exactly the three formats the README lists, with month/day order for the slash format, and raises on anything else.
