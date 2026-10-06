# set-064 answer key: Overnight queue simulation with retries

**Domain:** job_scheduler  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_dispatch.TestDispatch.test_1_etl_schedule` | B1 Priority order reversed |
| `test_1_dispatch.TestDispatch.test_2_training_outcomes` | B2 One retry too few |
| `test_2_jobs.TestJobs.test_3_reports_dependencies` | B3 Dependency ids only trimmed |
| `test_2_jobs.TestJobs.test_4_ops_wait_minutes` | B4 Wait uses timedelta.seconds |
| `test_3_summary.TestSummary.test_5_attempts_for_etl_and_ops` | B5 Queue logs share one default list |
| `test_3_summary.TestSummary.test_6_late_jobs` | B6 Finishing on the deadline counted as late |

## Failing pattern with all bugs present

- `tests.test_1_dispatch.TestDispatch.test_1_etl_schedule`
- `tests.test_1_dispatch.TestDispatch.test_2_training_outcomes`
- `tests.test_2_jobs.TestJobs.test_3_reports_dependencies`
- `tests.test_2_jobs.TestJobs.test_4_ops_wait_minutes`
- `tests.test_3_summary.TestSummary.test_5_attempts_for_etl_and_ops`
- `tests.test_3_summary.TestSummary.test_6_late_jobs`

## Bugs (recommended order)

### B1: Priority order reversed

- **Type:** sort-direction
- **Symptom:** Test 1 test_1_etl_schedule: etl-3 (priority 3) runs first at 00:00 and etl-2/etl-4 (priority 1) run last. The other queues' timelines are unchanged.
- **Location:** `nightshift/dispatcher.py` → `dispatch_order`
- **Why it fails:** Negating the priority puts the highest number first, but in this repo priority 1 is the most urgent. Only the etl queue ever has ready jobs of different priorities competing for a slot, so only its timeline moves.
- **Failing test:** `test_1_dispatch.TestDispatch.test_1_etl_schedule`
- **Unblocks:** test_1_etl_schedule.

Fix:

```diff
-    return sorted(ready, key=lambda j: (-j.priority, j.submitted_at, j.job_id))
+    return sorted(ready, key=lambda j: (j.priority, j.submitted_at, j.job_id))
```

Observed with only this bug applied (`tests.test_1_dispatch.TestDispatch.test_1_etl_schedule`):

```
AssertionError: {'etl-1': ('00:15', '00:45'), 'etl-2': ('00:55', '01:15'[84 chars]55')} != {'etl-1': ('00:45', '01:15'), 'etl-2': ('00:00', '00:20'[84 chars]25')}
- {'etl-1': ('00:15', '00:45'),
-  'etl-2': ('00:55', '01:15'),
? ^     ^        ^

+ {'etl-1': ('00:45', '01:15'),
? ^     ^        ^

-  'etl-3': ('00:00', '00:15'),
?       ^                 ^^

+  'etl-2': ('00:00', '00:20'),
?       ...
```

### B2: One retry too few

- **Type:** retry-off-by-one
- **Symptom:** Test 1 test_2_training_outcomes: trn-1 is failed after 2 attempts (finished None) and trn-2 is blocked with 0 attempts.
- **Location:** `nightshift/retry.py` → `should_retry`
- **Why it fails:** `job.attempts` already counts the failed attempt, so with max_retries 2 the job must still retry after attempt 2. `<` stops at max_retries attempts in total, so trn-1 fails after two attempts and its dependent trn-2 is blocked.
- **Failing test:** `test_1_dispatch.TestDispatch.test_2_training_outcomes`
- **Unblocks:** test_2_training_outcomes.

Fix:

```diff
-    return job.attempts < job.max_retries
+    return job.attempts <= job.max_retries
```

Observed with only this bug applied (`tests.test_1_dispatch.TestDispatch.test_2_training_outcomes`):

```
AssertionError: {'trn-1': ('failed', 2, None), 'trn-2': ('blocked', 0[34 chars]20')} != {'trn-1': ('done', 3, '03:40'), 'trn-2': ('done', 1, [35 chars]20')}
- {'trn-1': ('failed', 2, None),
-  'trn-2': ('blocked', 0, None),
+ {'trn-1': ('done', 3, '03:40'),
+  'trn-2': ('done', 1, '04:10'),
   'trn-3': ('done', 1, '01:20')}
```

### B3: Dependency ids only trimmed

- **Type:** id-normalization
- **Symptom:** Test 2 test_3_reports_dependencies: rpt-2 is blocked with no start or finish; rpt-1, rpt-3 and rpt-4 are unchanged.
- **Location:** `nightshift/loader.py` → `load_jobs`
- **Why it fails:** Job ids are lower-cased but the dependency list is only trimmed, so rpt-2's `RPT-1` never matches a job and deps_done is never true. rpt-4's lower-case dependencies still match.
- **Failing test:** `test_2_jobs.TestJobs.test_3_reports_dependencies`
- **Unblocks:** test_3_reports_dependencies.

Fix:

```diff
-                depends_on=[d.strip() for d in split_deps(r["depends_on"])],
+                depends_on=[norm_id(d) for d in split_deps(r["depends_on"])],
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobs.test_3_reports_dependencies`):

```
AssertionError: {'rpt[39 chars]': ('blocked', None, None), 'rpt-3': ('done', [50 chars]00')} != {'rpt[39 chars]': ('done', '00:45', '01:00'), 'rpt-3': ('done[53 chars]00')}
  {'rpt-1': ('done', '00:00', '00:45'),
-  'rpt-2': ('blocked', None, None),
+  'rpt-2': ('done', '00:45', '01:00'),
   'rpt-3': ('done', '00:30', '00:50'),
   'rpt-4': ('done', '00:50', '01:00')}
```

### B4: Wait uses timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 2 test_4_ops_wait_minutes: ops-1 shows 150 instead of 1590; the other waits are right.
- **Location:** `nightshift/timeutil.py` → `minutes_between`
- **Why it fails:** `timedelta.seconds` is only the seconds part after whole days are taken out. ops-1 waited 1 day 2 h 30 min, and `.seconds` drops the day, giving 150 instead of 1590.
- **Failing test:** `test_2_jobs.TestJobs.test_4_ops_wait_minutes`
- **Unblocks:** test_4_ops_wait_minutes.

Fix:

```diff
-    return int((later - earlier).seconds // 60)
+    return int((later - earlier).total_seconds() // 60)
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobs.test_4_ops_wait_minutes`):

```
AssertionError: {'ops-1': 150, 'ops-2': 50, 'ops-3': 0, 'ops-4': 20} != {'ops-1': 1590, 'ops-2': 50, 'ops-3': 0, 'ops-4': 20}
- {'ops-1': 150, 'ops-2': 50, 'ops-3': 0, 'ops-4': 20}
+ {'ops-1': 1590, 'ops-2': 50, 'ops-3': 0, 'ops-4': 20}
?             +
```

### B5: Queue logs share one default list

- **Type:** mutable-default
- **Symptom:** Test 3 test_5_attempts_for_etl_and_ops: etl and ops both show the same inflated count (57 when the whole suite runs, since every build_report() call adds 19 attempts to one shared list) instead of 5 and 5.
- **Location:** `nightshift/models.py` → `QueueLog.__init__`
- **Why it fails:** A default `[]` is created once, when the function is defined, so every QueueLog built without entries appends to the same list. All four queues end up reporting the same length, and because the list lives at module level it keeps growing every time build_report() runs in the same process.
- **Failing test:** `test_3_summary.TestSummary.test_5_attempts_for_etl_and_ops`
- **Unblocks:** test_5_attempts_for_etl_and_ops.

Fix:

```diff
-    def __init__(self, name, entries=[]):
+    def __init__(self, name, entries=None):
         self.name = name
-        self.entries = entries
+        self.entries = [] if entries is None else entries
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_5_attempts_for_etl_and_ops`):

```
AssertionError: {'etl': 57, 'ops': 57} != {'etl': 5, 'ops': 5}
- {'etl': 57, 'ops': 57}
?          -          -

+ {'etl': 5, 'ops': 5}
```

### B6: Finishing on the deadline counted as late

- **Type:** time-window-boundary
- **Symptom:** Test 3 test_6_late_jobs: ops-1, which finishes exactly at its 00:40 deadline, is listed as late.
- **Location:** `nightshift/report.py` → `is_late`
- **Why it fails:** The spec says finishing exactly at the deadline is on time. `>=` makes ops-1, which finishes at its 00:40 deadline, late.
- **Failing test:** `test_3_summary.TestSummary.test_6_late_jobs`
- **Unblocks:** test_6_late_jobs.

Fix:

```diff
-job.finished_at >= job.deadline
+job.finished_at > job.deadline
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_6_late_jobs`):

```
AssertionError: Lists differ: ['ops-1', 'ops-2', 'ops-3'] != ['ops-2', 'ops-3']

First differing element 0:
'ops-1'
'ops-2'

First list contains 1 additional elements.
First extra element 2:
'ops-3'

- ['ops-1', 'ops-2', 'ops-3']
?  ---------

+ ['ops-2', 'ops-3']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `nightshift/retry.py` → `next_ready_at`: Rule 5 asks for backoff_min × n after the n-th failed attempt, and the dispatcher passes job.attempts, which already counts the failed attempt. Multiplying by the attempt number looks like it should be an exponent or n-1, but linear backoff is exactly what the spec says.
