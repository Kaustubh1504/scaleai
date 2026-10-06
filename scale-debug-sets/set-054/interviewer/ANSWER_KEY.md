# set-054 answer key: Two-level review flow: four-eyes state machine

**Domain:** review_state_machine  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_transitions.TestTransitions.test_rejection_reasons` | B1 Broad except clause catches conflicts first |
| `test_2_tasks.TestTasks.test_history` | B2 History list shared by every task |
| `test_2_tasks.TestTasks.test_waiting_queue` | B3 reverse=True also reverses the tie-breaks |
| `test_2_tasks.TestTasks.test_reviewer_stats` | B4 Actor names only trimmed |
| `test_3_report.TestReport.test_cycle_hours` | B5 timedelta.seconds drops whole days |
| `test_3_report.TestReport.test_approval_rate` | B6 Enum state compared to a string |

## Failing pattern with all bugs present

- `tests.test_1_transitions.TestTransitions.test_rejection_reasons`
- `tests.test_2_tasks.TestTasks.test_history`
- `tests.test_2_tasks.TestTasks.test_reviewer_stats`
- `tests.test_2_tasks.TestTasks.test_waiting_queue`
- `tests.test_3_report.TestReport.test_approval_rate`
- `tests.test_3_report.TestReport.test_cycle_hours`

## Bugs (recommended order)

### B1: Broad except clause catches conflicts first

- **Type:** exception-order
- **Symptom:** Test 1 test_rejection_reasons: the three conflict_of_interest entries (rae on T1, cho on T3, eli on T8) show 'not_assignee'. The refused events themselves are right.
- **Location:** `reviewflow/machine.py` → `ReviewMachine.handle`
- **Why it fails:** ConflictOfInterest subclasses AssignmentError, and Python uses the first except clause that matches. With the parent clause first, every conflict is labelled not_assignee and the conflict branch can never run.
- **Failing test:** `test_1_transitions.TestTransitions.test_rejection_reasons`
- **Unblocks:** test_rejection_reasons.

Fix:

```diff
+        except ConflictOfInterest:
+            self.rejected.append((event, "conflict_of_interest"))
         except AssignmentError:
             self.rejected.append((event, "not_assignee"))
-        except ConflictOfInterest:
-            self.rejected.append((event, "conflict_of_interest"))
```

Observed with only this bug applied (`tests.test_1_transitions.TestTransitions.test_rejection_reasons`):

```
AssertionError: Lists differ: ['not_assignee', 'not_assignee', 'invalid_t[98 chars]ion'] != ['conflict_of_interest', 'conflict_of_inter[122 chars]ion']

First differing element 0:
'not_assignee'
'conflict_of_interest'

- ['not_assignee',
-  'not_assignee',
+ ['conflict_of_interest',
+  'conflict_of_interest',
   'invalid_transition',
   'not_assignee',
   'unknown_task',
-  'not_assignee',
+  'con ...
```

### B2: History list shared by every task

- **Type:** shared-class-attribute
- **Symptom:** Test 2 test_history: T1's history is one long list beginning 'submitted', 'submitted', 'submitted', ... (88 entries in a full run) instead of 5 states. Every task returns that same list.
- **Location:** `reviewflow/models.py` → `Task.__init__`
- **Why it fails:** `history = []` on the class is a single list. append() mutates it through every instance, unlike `self.state = ...`, which creates a per-instance attribute. So all tasks share one ever-growing history.
- **Failing test:** `test_2_tasks.TestTasks.test_history`
- **Unblocks:** test_history.

Fix:

```diff
     decided_at = None
-    history = []
 
     def __init__(self, task_id, author, priority, submitted_at):
         self.submitted_at = submitted_at
         self.entered_at = submitted_at
+        self.history = []
```

Observed with only this bug applied (`tests.test_2_tasks.TestTasks.test_history`):

```
AssertionError: Lists differ: ['submitted', 'submitted', 'submitted', 'submitted', 'su[1125 chars]ted'] != ['submitted', 'l1_review', 'awaiting_l2', 'l2_review', 'approved']

First differing element 1:
'submitted'
'l1_review'

First list contains 83 additional elements.
First extra element 5:
'submitted'

Diff is 1519 characters long. Set self.maxDiff to None to see it.
```

### B3: reverse=True also reverses the tie-breaks

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_waiting_queue: the priority-2 tasks come out T7, T12, T11 instead of T11, T12, T7. T2 is still first and T10 still last.
- **Location:** `reviewflow/backlog.py` → `waiting_queue`
- **Why it fails:** reverse=True flips the whole key, so among equal priorities the most recently queued task comes first instead of the one that has waited longest.
- **Failing test:** `test_2_tasks.TestTasks.test_waiting_queue`
- **Unblocks:** test_waiting_queue.

Fix:

```diff
-    waiting.sort(key=lambda t: (t.priority, t.entered_at, t.task_id), reverse=True)
+    waiting.sort(key=lambda t: (-t.priority, t.entered_at, t.task_id))
```

Observed with only this bug applied (`tests.test_2_tasks.TestTasks.test_waiting_queue`):

```
AssertionError: Lists differ: [['T2[15 chars], ['T7', 'awaiting_l2'], ['T12', 'submitted'],[39 chars]ed']] != [['T2[15 chars], ['T11', 'submitted'], ['T12', 'submitted'], [39 chars]ed']]

First differing element 1:
['T7', 'awaiting_l2']
['T11', 'submitted']

  [['T2', 'submitted'],
+  ['T11', 'submitted'],
+  ['T12', 'submitted'],
   ['T7', 'awaiting_l2'],
-  ['T12', 'submitted'],
-  ['T11', 'subm ...
```

### B4: Actor names only trimmed

- **Type:** id-normalization
- **Symptom:** Test 2 test_reviewer_stats: the table has both 'Dana' {passed 1, changes 1} and 'dana' {passed 1} instead of one 'dana' {passed 2, changes 1}.
- **Location:** `reviewflow/loader.py` → `load_events`
- **Why it fails:** Authors are lower-cased but actors are only trimmed, so 'Dana' and 'dana' count as two reviewers. Each spelling is used consistently within a task, so the state machine still works and only the stats split.
- **Failing test:** `test_2_tasks.TestTasks.test_reviewer_stats`
- **Unblocks:** test_reviewer_stats.

Fix:

```diff
-                actor=clean(row["actor"]),
+                actor=norm_person(row["actor"]),
```

Observed with only this bug applied (`tests.test_2_tasks.TestTasks.test_reviewer_stats`):

```
AssertionError: {'Dana': {'passed': 1, 'changes': 1, 'rejec[209 chars]: 1}} != {'dana': {'passed': 2, 'changes': 1, 'rejec[157 chars]: 1}}
- {'Dana': {'changes': 1, 'passed': 1, 'rejected': 0},
?   ^                               ^

+ {'dana': {'changes': 1, 'passed': 2, 'rejected': 0},
?   ^                               ^

-  'dana': {'changes': 0, 'passed': 1, 'rejected': 0},
   'lee': {'change ...
```

### B5: timedelta.seconds drops whole days

- **Type:** timedelta-seconds
- **Symptom:** Test 3 test_cycle_hours: T3 is 0.5 instead of 24.5. Every other task matches.
- **Location:** `reviewflow/metrics.py` → `cycle_hours`
- **Why it fails:** `timedelta.seconds` is only the seconds part after removing whole days (0–86399). T3's 24.5 hours becomes 0.5.
- **Failing test:** `test_3_report.TestReport.test_cycle_hours`
- **Unblocks:** test_cycle_hours.

Fix:

```diff
-            out[task.task_id] = round(elapsed.seconds / 3600, 1)
+            out[task.task_id] = round(elapsed.total_seconds() / 3600, 1)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_cycle_hours`):

```
AssertionError: {'T1': 2.2, 'T3': 0.5, 'T4': 6.0, 'T5': 3.5, 'T6': 21.5, 'T8': 23.7, 'T9': 3.0} != {'T1': 2.2, 'T3': 24.5, 'T4': 6.0, 'T5': 3.5, 'T6': 21.5, 'T8': 23.7, 'T9': 3.0}
- {'T1': 2.2, 'T3': 0.5, 'T4': 6.0, 'T5': 3.5, 'T6': 21.5, 'T8': 23.7, 'T9': 3.0}
?                   ^

+ {'T1': 2.2, 'T3': 24.5, 'T4': 6.0, 'T5': 3.5, 'T6': 21.5, 'T8': 23.7, 'T9': 3.0}
?                   ^^
```

### B6: Enum state compared to a string

- **Type:** enum-vs-string
- **Symptom:** Test 3 test_approval_rate: `0.0 != 0.571`. by_state still shows 4 approved.
- **Location:** `reviewflow/reports.py` → `summarize`
- **Why it fails:** State is a plain Enum, so State.APPROVED == 'approved' is False. No task counts as approved and the rate becomes 0.0, while by_state (which uses .value) is still right.
- **Failing test:** `test_3_report.TestReport.test_approval_rate`
- **Unblocks:** test_approval_rate.

Fix:

```diff
-    approved = sum(1 for t in tasks if t.state == "approved")
+    approved = sum(1 for t in tasks if t.state is State.APPROVED)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_approval_rate`):

```
AssertionError: 0.0 != 0.571
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `reviewflow/loader.py` → `parse_time`: It tries exactly the three formats in the README, month/day for the slash form, and raises on anything else rather than guessing.
- `reviewflow/machine.py` → `check_claim`: Authors can never claim, and the level-1 reviewer is only blocked at level 2. Both raise ConflictOfInterest, which is a subclass of AssignmentError, so the handler has to catch it first.
