# set-078 answer key: Review lifecycle replay with claim expiry and escalation

**Domain:** review_state_machine  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_lifecycle.TestLifecycle.test_final_states` | B1 Claim treated as expired at its deadline |
| `test_1_lifecycle.TestLifecycle.test_violations` | B2 Duplicate key uses the raw actor id |
| `test_2_reviewers.TestReviewers.test_reviewer_decisions` | B3 `or` makes every decision count as approved |
| `test_2_reviewers.TestReviewers.test_review_minutes` | B4 Review samples stored on the class |
| `test_3_report.TestReport.test_queue` | B5 Removing paused tasks while iterating the queue |
| `test_3_report.TestReport.test_cycle_hours` | B6 Cycle time uses timedelta.seconds |

## Failing pattern with all bugs present

- `tests.test_1_lifecycle.TestLifecycle.test_final_states`
- `tests.test_1_lifecycle.TestLifecycle.test_violations`
- `tests.test_2_reviewers.TestReviewers.test_review_minutes`
- `tests.test_2_reviewers.TestReviewers.test_reviewer_decisions`
- `tests.test_3_report.TestReport.test_cycle_hours`
- `tests.test_3_report.TestReport.test_queue`

## Bugs (recommended order)

### B1: Claim treated as expired at its deadline

- **Type:** time-window-boundary
- **Symptom:** Test 1 test_final_states: T-10 ends as 'submitted' instead of 'in_review'. Nothing else changes, not even the queue, because T-10's project (beta) is paused.
- **Location:** `revflow/clock.py` → `claim_expired`
- **Why it fails:** T-10 was claimed at 16:30 with a 90-minute TTL, so its deadline is exactly as_of (18:00). The spec says an action exactly at the deadline is still in time, but `>=` releases the claim in the final sweep.
- **Failing test:** `test_1_lifecycle.TestLifecycle.test_final_states`
- **Unblocks:** test_final_states

Fix:

```diff
-    return now >= deadline
+    return now > deadline
```

Observed with only this bug applied (`tests.test_1_lifecycle.TestLifecycle.test_final_states`):

```
AssertionError: {'T-0[186 chars]0': 'submitted', 'T-11': 'submitted', 'T-12': [45 chars]ued'} != {'T-0[186 chars]0': 'in_review', 'T-11': 'submitted', 'T-12': [45 chars]ued'}
  {'T-01': 'approved',
   'T-02': 'approved',
   'T-03': 'approved',
   'T-04': 'submitted',
   'T-05': 'submitted',
   'T-06': 'submitted',
   'T-07': 'submitted',
   'T-08': 'submitted',
   'T-09': 'submitted',
-  'T-10': ' ...
```

### B2: Duplicate key uses the raw actor id

- **Type:** id-normalization
- **Symptom:** Test 1 test_violations: an extra first entry `{'line': 8, 'task': 'T-01', 'action': 'approve', 'reason': 'invalid transition'}`. States, rework and reviewer counts are unchanged.
- **Location:** `revflow/loader.py` → `load_events`
- **Why it fails:** Line 8 repeats line 7's approve with actor `RV-01`. The dedupe key keeps the raw case, so the copy survives. Replaying it on an already-approved task adds an `invalid transition` violation, while the task itself and the stats are unchanged.
- **Failing test:** `test_1_lifecycle.TestLifecycle.test_violations`
- **Unblocks:** test_violations

Fix:

```diff
-            key = (ts, task_id, clean(row["actor"]), action)
+            key = (ts, task_id, actor, action)
```

Observed with only this bug applied (`tests.test_1_lifecycle.TestLifecycle.test_violations`):

```
AssertionError: Lists differ: [{'line': 8, 'task': 'T-01', 'action': 'approve', '[696 chars]ed'}] != [{'line': 18, 'task': 'T-03', 'action': 'resolve', [614 chars]ed'}]

First differing element 0:
{'line': 8, 'task': 'T-01', 'action': 'approve', 'reason': 'invalid transition'}
{'line': 18, 'task': 'T-03', 'action': 'resolve', 'reason': 'actor not allowed'}

First list contains 1 additional element ...
```

### B3: `or` makes every decision count as approved

- **Type:** or-precedence
- **Symptom:** Test 2 test_reviewer_decisions: rv-02 shows approved 1 / rejected 0 (should be 0 / 1) and rv-03 approved 2 / rejected 0 (should be 0 / 2). Claims are correct.
- **Location:** `revflow/stats.py` → `reviewer_decisions`
- **Why it fails:** `t.action == "approve" or "resolve"` parses as `(t.action == "approve") or "resolve"`, and the non-empty string is always truthy. Every non-claim transition, rejects included, lands in `approved`.
- **Failing test:** `test_2_reviewers.TestReviewers.test_reviewer_decisions`
- **Unblocks:** test_reviewer_decisions

Fix:

```diff
-            elif t.action == "approve" or "resolve":
+            elif t.action == "approve" or t.action == "resolve":
```

Observed with only this bug applied (`tests.test_2_reviewers.TestReviewers.test_reviewer_decisions`):

```
AssertionError: {'rv-[80 chars]ed': 1, 'rejected': 0}, 'rv-03': {'claims': 3,[134 chars]: 0}} != {'rv-[80 chars]ed': 0, 'rejected': 1}, 'rv-03': {'claims': 3,[134 chars]: 0}}
  {'rv-01': {'approved': 2, 'claims': 3, 'rejected': 0},
-  'rv-02': {'approved': 1, 'claims': 3, 'rejected': 0},
?                        ^                           ^

+  'rv-02': {'approved': 0, 'claims': 3, 'rejected': 1} ...
```

### B4: Review samples stored on the class

- **Type:** shared-class-attribute
- **Symptom:** Test 2 test_review_minutes: `{'rv-01': 31.0, 'rv-02': 31.0, 'rv-03': 31.0} != {'rv-01': 37.5, 'rv-02': 30.0, 'rv-03': 25.0}`. Every reviewer gets the same mean.
- **Location:** `revflow/stats.py` → `ReviewTimer`
- **Why it fails:** With `samples = []` at class level and no per-instance list, every ReviewTimer appends to the same list. Each reviewer's mean is then the mean over all decisions (31.0).
- **Failing test:** `test_2_reviewers.TestReviewers.test_review_minutes`
- **Unblocks:** test_review_minutes

Fix:

```diff
-    samples = []
+    samples: list
 
     def __init__(self, reviewer):
         self.reviewer = reviewer
+        self.samples = []
```

Observed with only this bug applied (`tests.test_2_reviewers.TestReviewers.test_review_minutes`):

```
AssertionError: {'rv-01': 31.0, 'rv-02': 31.0, 'rv-03': 31.0} != {'rv-01': 37.5, 'rv-02': 30.0, 'rv-03': 25.0}
- {'rv-01': 31.0, 'rv-02': 31.0, 'rv-03': 31.0}
?            ^ ^            ^             ^^

+ {'rv-01': 37.5, 'rv-02': 30.0, 'rv-03': 25.0}
?            ^ ^            ^             ^^
```

### B5: Removing paused tasks while iterating the queue

- **Type:** mutate-while-iterating
- **Symptom:** Test 3 test_queue: `['T-07', 'T-08', 'T-09', 'T-04', 'T-05', 'T-11']`. T-07 (paused project delta) is still at the front.
- **Location:** `revflow/backlog.py` → `build_queue`
- **Why it fails:** Removing T-06 shifts T-07 into the slot the loop has already passed, so the loop never looks at T-07 and the paused delta task stays in the queue.
- **Failing test:** `test_3_report.TestReport.test_queue`
- **Unblocks:** test_queue

Fix:

```diff
-    for task in queue:
+    for task in list(queue):
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_queue`):

```
AssertionError: Lists differ: ['T-07', 'T-08', 'T-09', 'T-04', 'T-05', 'T-11'] != ['T-08', 'T-09', 'T-04', 'T-05', 'T-11']

First differing element 0:
'T-07'
'T-08'

First list contains 1 additional elements.
First extra element 5:
'T-11'

- ['T-07', 'T-08', 'T-09', 'T-04', 'T-05', 'T-11']
?  --------

+ ['T-08', 'T-09', 'T-04', 'T-05', 'T-11']
```

### B6: Cycle time uses timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 3 test_cycle_hours: T-02 shows 3.0 instead of 27.0; T-01 and T-03 are correct.
- **Location:** `revflow/reports.py` → `cycle_hours`
- **Why it fails:** timedelta.seconds is only the seconds part after whole days are taken out. T-02 took 1 day 3 hours, so `.seconds` gives 3 hours. The other tasks took less than a day and look correct.
- **Failing test:** `test_3_report.TestReport.test_cycle_hours`
- **Unblocks:** test_cycle_hours

Fix:

```diff
-(t.approved_at - t.created).seconds / 3600
+(t.approved_at - t.created).total_seconds() / 3600
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_cycle_hours`):

```
AssertionError: {'T-01': 3.0, 'T-02': 3.0, 'T-03': 20.0} != {'T-01': 3.0, 'T-02': 27.0, 'T-03': 20.0}
- {'T-01': 3.0, 'T-02': 3.0, 'T-03': 20.0}
?                       ^

+ {'T-01': 3.0, 'T-02': 27.0, 'T-03': 20.0}
?                       ^^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `revflow/machine.py` → `next_state`: Sending a reject back to LABELING instead of a 'rejected' state looks odd, but it is exactly the README table. The escalation compares the rework count *after* this reject with max_rework, so the second reject escalates when max_rework is 2.
- `revflow/backlog.py` → `priority_key`: -priority looks like a flipped sort, but the README says the higher number is more urgent, so negating it puts the most urgent first. Oldest created first and then task id match the spec.
