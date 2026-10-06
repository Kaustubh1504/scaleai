# set-040 answer key: Batch job scheduler: queue order, blocked deps, team summary

**Domain:** job_scheduler  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_schedule.TestSchedule.test_morning_wave` | B1 Queue modified while iterating it |
| `test_1_schedule.TestSchedule.test_afternoon_wave` | B2 Release time missing from the queue tie-break |
| `test_2_jobs.TestJobs.test_blocked` | B3 Only the first dependency is checked |
| `test_2_jobs.TestJobs.test_event_log` | B4 Event log shared between all jobs |
| `test_3_report.TestReport.test_teams` | B5 groupby over unsorted jobs |
| `test_3_report.TestReport.test_late` | B6 Finishing exactly at the deadline counted as late |

## Failing pattern with all bugs present

- `tests.test_1_schedule.TestSchedule.test_afternoon_wave`
- `tests.test_1_schedule.TestSchedule.test_morning_wave`
- `tests.test_2_jobs.TestJobs.test_blocked`
- `tests.test_2_jobs.TestJobs.test_event_log`
- `tests.test_3_report.TestReport.test_late`
- `tests.test_3_report.TestReport.test_teams`

## Bugs (recommended order)

### B1: Queue modified while iterating it

- **Type:** mutate-while-iterating
- **Symptom:** Test 1 test_morning_wave: m3 runs 06:00-06:30 on w2 and m2 waits until 06:30-07:15, although m2 (priority 5) outranks m3 (priority 3) and two workers were free at 06:00.
- **Location:** `jobsim/scheduler.py` → `simulate`
- **Why it fails:** queue.remove(state) inside the loop shifts the list, so the iterator skips the next element. At 06:00 m1 starts, m2 is skipped, and m3 takes w2. This only matters when two or more workers are free at once, which happens only at the start of the morning wave.
- **Failing test:** `test_1_schedule.TestSchedule.test_morning_wave`
- **Unblocks:** Test 1 test_morning_wave.

Fix:

```diff
-        for state in queue:
+        for state in list(queue):
```

Observed with only this bug applied (`tests.test_1_schedule.TestSchedule.test_morning_wave`):

```
AssertionError: {'m1'[145 chars] '06:30', 'end': '07:15', 'worker': 'w2'}, 'm3[279 chars]w1'}} != {'m1'[145 chars] '06:00', 'end': '06:45', 'worker': 'w2'}, 'm3[279 chars]w1'}}
  {'m1': {'attempts': 1,
          'end': '07:00',
          'start': '06:00',
          'status': 'succeeded',
          'worker': 'w1'},
   'm2': {'attempts': 1,
-         'end': '07:15',
?                  ^ ^

+         ...
```

### B2: Release time missing from the queue tie-break

- **Type:** wrong-tie-break
- **Symptom:** Test 1 test_afternoon_wave: a2 starts at 13:42 on w2 and a3 at 14:00 on w1; it should be the other way round (a3 was released earlier, same priority).
- **Location:** `jobsim/models.py` → `Job.queue_key`
- **Why it fails:** a2 and a3 are both priority 4. a3 was released at 13:05 and a2 at 13:10, so a3 should go first, but without release in the key the id decides and a2 wins.
- **Failing test:** `test_1_schedule.TestSchedule.test_afternoon_wave`
- **Unblocks:** Test 1 test_afternoon_wave.

Fix:

```diff
-        return (-self.priority, self.job_id)
+        return (-self.priority, self.release, self.job_id)
```

Observed with only this bug applied (`tests.test_1_schedule.TestSchedule.test_afternoon_wave`):

```
AssertionError: {'a9'[239 chars]': '14:00', 'end': '14:30', 'worker': 'w1'}, '[185 chars]w2'}} != {'a9'[239 chars]': '13:42', 'end': '14:12', 'worker': 'w2'}, '[185 chars]w2'}}
  {'a1': {'attempts': 1,
          'end': '13:42',
          'start': '13:02',
          'status': 'succeeded',
          'worker': 'w2'},
   'a2': {'attempts': 1,
+         'end': '14:30',
+         'start': '14:00',
+     ...
```

### B3: Only the first dependency is checked

- **Type:** early-return
- **Symptom:** Test 2 test_blocked: b1 is missing from blocked ({b2, c1, c2} only), and its status is skipped rather than blocked.
- **Location:** `jobsim/dag.py` → `missing_dep`
- **Why it fails:** The `return None` is inside the loop, so the function gives up after the first dependency. b1's first dep (m1) exists, so its missing second dep zz-missing is never seen; b1 is not blocked and just waits until it is skipped at the end of the day.
- **Failing test:** `test_2_jobs.TestJobs.test_blocked`
- **Unblocks:** Test 2 test_blocked.

Fix:

```diff
             return dep
-        return None
+    return None
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobs.test_blocked`):

```
AssertionError: {'b2': 'missing_dep:ghost', 'c1': 'cycle', 'c2': 'cycle'} != {'b1': 'missing_dep:zz-missing', 'b2': 'miss[40 chars]cle'}
- {'b2': 'missing_dep:ghost', 'c1': 'cycle', 'c2': 'cycle'}
+ {'b1': 'missing_dep:zz-missing',
+  'b2': 'missing_dep:ghost',
+  'c1': 'cycle',
+  'c2': 'cycle'}
```

### B4: Event log shared between all jobs

- **Type:** mutable-default
- **Symptom:** Test 2 test_event_log: m5's log holds every event of the day (starts on both workers, the afternoon wave) instead of its own 4 entries.
- **Location:** `jobsim/models.py` → `JobState.__init__`
- **Why it fails:** The default list is created once, when the function is defined. Every JobState built without events gets that same list, so each job's log holds the whole day's events.
- **Failing test:** `test_2_jobs.TestJobs.test_event_log`
- **Unblocks:** Test 2 test_event_log.

Fix:

```diff
-    def __init__(self, job, events=[]):
+    def __init__(self, job, events=None):
         self.job = job
-        self.events = events
+        self.events = list(events or [])
```

Observed with only this bug applied (`tests.test_2_jobs.TestJobs.test_event_log`):

```
AssertionError: Lists differ: ['start@06:00/w1', 'start@06:00/w2', 'done@06:45',[777 chars]:40'] != ['start@07:00/w1', 'fail@07:20', 'start@07:35/w1', 'done@07:55']

First differing element 0:
'start@06:00/w1'
'start@07:00/w1'

First list contains 48 additional elements.
First extra element 4:
'done@07:00'

+ ['start@07:00/w1', 'fail@07:20', 'start@07:35/w1', 'done@07:55']
- ['start@06:00/w1',
-   ...
```

### B5: groupby over unsorted jobs

- **Type:** groupby-misuse
- **Symptom:** Test 3 test_teams: etl shows jobs 2 / succeeded 0 / busy 0, ml/bi/ops show 1 job each with 0 busy; the real totals are bi 5/4/105, etl 6/4/205, ml 4/3/90, ops 3/0/10.
- **Location:** `jobsim/reports.py` → `team_summary`
- **Why it fails:** itertools.groupby only groups consecutive items. In file order the teams are interleaved, so each team comes up several times and summary[team] is overwritten by its last run (e.g. etl ends up as just c1 and c2).
- **Failing test:** `test_3_report.TestReport.test_teams`
- **Unblocks:** Test 3 test_teams.

Fix:

```diff
-    for team, group in groupby(states.values(), key=lambda s: s.job.team):
+    ordered = sorted(states.values(), key=lambda s: s.job.team)
+    for team, group in groupby(ordered, key=lambda s: s.job.team):
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_teams`):

```
AssertionError: {'etl': {'jobs': 2, 'succeeded': 0, 'busy_m[154 chars]: 0}} != {'bi': {'jobs': 5, 'succeeded': 4, 'busy_mi[160 chars] 10}}
- {'bi': {'busy_min': 0, 'jobs': 1, 'succeeded': 0},
?                                ^               ^

+ {'bi': {'busy_min': 105, 'jobs': 5, 'succeeded': 4},
?                     + +          ^               ^

-  'etl': {'busy_min': 0, 'jobs': 2, 'succeeded ...
```

### B6: Finishing exactly at the deadline counted as late

- **Type:** time-window-boundary
- **Symptom:** Test 3 test_late: ["a6", "a9"] instead of ["a6"]; a9 ends exactly at its 14:00 deadline.
- **Location:** `jobsim/reports.py` → `late_jobs`
- **Why it fails:** a9 ends at 14:00 with a 14:00 deadline. The README says that is on time; >= reports it as late.
- **Failing test:** `test_3_report.TestReport.test_late`
- **Unblocks:** Test 3 test_late.

Fix:

```diff
-s.end >= s.job.deadline)
+s.end > s.job.deadline)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_late`):

```
AssertionError: Lists differ: ['a6', 'a9'] != ['a6']

First list contains 1 additional elements.
First extra element 1:
'a9'

- ['a6', 'a9']
+ ['a6']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `jobsim/timeparse.py` → `parse_duration`: The regex makes both parts optional, which looks like it would accept an empty string, but `not any(match.groups())` rejects that. Bare digits are minutes (m4's '30'), and '1h' / '45m' / '1h30m' all parse to the right minute counts.
- `jobsim/dag.py` → `cycle_members`: A DFS with open/done states; meeting an 'open' node means the path from that node to here is a cycle, so path[path.index(dep):] is exactly the cycle (c1, c2). Unknown deps are skipped here because missing_dep reports them. c3 depends on the cycle but is not on it, so it is not blocked; it ends up skipped.
