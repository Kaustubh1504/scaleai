# set-088 answer key: Batch cluster day planner with retries and dependencies

**Domain:** job_scheduler  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_intake.TestIntake.test_1_dependencies` | B1 Dependency ids not upper-cased |
| `test_2_schedule.TestSchedule.test_2_cpu_lane` | B2 Least urgent job dispatched first |
| `test_2_schedule.TestSchedule.test_3_io_lane` | B3 One retry too few |
| `test_2_schedule.TestSchedule.test_4_gpu_lane` | B4 max_retries 0 replaced by the default |
| `test_3_report.TestReport.test_5_longest_wait` | B5 Wait loses whole days |
| `test_3_report.TestReport.test_6_pool_capacity` | B6 Inactive workers counted as slots |

## Failing pattern with all bugs present

- `tests.test_1_intake.TestIntake.test_1_dependencies`
- `tests.test_2_schedule.TestSchedule.test_2_cpu_lane`
- `tests.test_2_schedule.TestSchedule.test_3_io_lane`
- `tests.test_2_schedule.TestSchedule.test_4_gpu_lane`
- `tests.test_3_report.TestReport.test_5_longest_wait`
- `tests.test_3_report.TestReport.test_6_pool_capacity`

## Bugs (recommended order)

### B1: Dependency ids not upper-cased

- **Type:** id-normalization
- **Symptom:** test_1_dependencies fails: G03 is missing from the dependency map (expected G03: ['G01']). Every schedule test still passes.
- **Location:** `batchsched/deps.py` → `parse_deps`
- **Why it fails:** G03's dependency is written ` g01`. Without `norm_job` it stays `g01`, which is not an accepted job id, so `resolve_deps` drops it. The schedule doesn't change, because gpu has one slot and G01 already holds it until G03 could start.
- **Failing test:** `test_1_intake.TestIntake.test_1_dependencies`
- **Unblocks:** test_1_dependencies.

Fix:

```diff
-    return [part.strip() for part in clean(raw).split(";") if part.strip()]
+    return [norm_job(part) for part in clean(raw).split(";") if part.strip()]
```

Observed with only this bug applied (`tests.test_1_intake.TestIntake.test_1_dependencies`):

```
AssertionError: {'I02': ['I01'], 'M04': ['M02', 'M03']} != {'G03': ['G01'], 'I02': ['I01'], 'M04': ['M02', 'M03']}
- {'I02': ['I01'], 'M04': ['M02', 'M03']}
+ {'G03': ['G01'], 'I02': ['I01'], 'M04': ['M02', 'M03']}
?  ++++++++++++++++
```

### B2: Least urgent job dispatched first

- **Type:** sort-direction
- **Symptom:** test_2_cpu_lane fails: C01 runs 08:00-08:40 and C02 (priority 5) waits until 08:40-09:00. Expected C02 08:00-08:20 and C01 08:20-09:00.
- **Location:** `batchsched/simulator.py` → `queue_key`
- **Why it fails:** Priority 5 is the most urgent, so the sort has to be descending on priority. Ascending dispatches C01 (2) and C03 (3) at 08:00 and leaves C02 (5) until 08:40. The other lanes never have two jobs of different priority competing for a slot, so only cpu changes.
- **Failing test:** `test_2_schedule.TestSchedule.test_2_cpu_lane`
- **Unblocks:** test_2_cpu_lane.

Fix:

```diff
-    return (job.priority, submit_offset[job.id], job.id)
+    return (-job.priority, submit_offset[job.id], job.id)
```

Observed with only this bug applied (`tests.test_2_schedule.TestSchedule.test_2_cpu_lane`):

```
AssertionError: {'C01[26 chars] '08:00', '08:40'), 'C02': ('succeeded', 1, 'w[118 chars]40')} != {'C01[26 chars] '08:20', '09:00'), 'C02': ('succeeded', 1, 'w[118 chars]40')}
- {'C01': ('succeeded', 1, 'w01', '08:00', '08:40'),
?                                     ^      ^ ^

+ {'C01': ('succeeded', 1, 'w01', '08:20', '09:00'),
?                                     ^      ^ ^

-  'C02': ('succeed ...
```

### B3: One retry too few

- **Type:** retry-off-by-one
- **Symptom:** test_3_io_lane fails: I01 is failed after 1 attempt (ends 08:15), I02 is blocked, and I03 runs 08:30-08:40. Expected I01 succeeded on attempt 2 at 08:35.
- **Location:** `batchsched/retry.py` → `should_retry`
- **Why it fails:** `attempts` includes the attempt that just failed, so a job with max_retries 1 must retry after attempt 1 (1 <= 1). With `<`, I01 is marked failed after its first attempt, I02 becomes blocked, and I03 moves up to 08:30.
- **Failing test:** `test_2_schedule.TestSchedule.test_3_io_lane`
- **Unblocks:** test_3_io_lane.

Fix:

```diff
-    return attempts < max_retries
+    return attempts <= max_retries
```

Observed with only this bug applied (`tests.test_2_schedule.TestSchedule.test_3_io_lane`):

```
AssertionError: {'I01': ('failed', 1, 'w06', '08:00', '08:15'), 'I0[82 chars]40')} != {'I01': ('succeeded', 2, 'w06', '08:00', '08:35'), [94 chars]55')}
- {'I01': ('failed', 1, 'w06', '08:00', '08:15'),
?           ^^^^     ^                      ^

+ {'I01': ('succeeded', 2, 'w06', '08:00', '08:35'),
?           ^^^^^^^     ^                      ^

-  'I02': ('blocked', 0, None, None, None),
-   ...
```

### B4: max_retries 0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** test_4_gpu_lane fails: G02 shows ('failed', 3, 'w04', '08:50', '09:35'). Expected 1 attempt ending 09:00.
- **Location:** `batchsched/loader.py` → `load_jobs`
- **Why it fails:** `int('0') or DEFAULT_RETRIES` treats an explicit 0 as missing, so G02 gets 2 retries. It still ends `failed` (all three scripted attempts fail), but with 3 attempts and an end of 09:35.
- **Failing test:** `test_2_schedule.TestSchedule.test_4_gpu_lane`
- **Unblocks:** test_4_gpu_lane.

Fix:

```diff
-                max_retries=int(retries or 0) or DEFAULT_RETRIES,
+                max_retries=int(retries) if retries else DEFAULT_RETRIES,
```

Observed with only this bug applied (`tests.test_2_schedule.TestSchedule.test_4_gpu_lane`):

```
AssertionError: {'G01[59 chars]ed', 3, 'w04', '08:50', '09:35'), 'G03': ('suc[32 chars]50')} != {'G01[59 chars]ed', 1, 'w04', '08:50', '09:00'), 'G03': ('suc[32 chars]50')}
  {'G01': ('succeeded', 1, 'w04', '08:00', '08:30'),
-  'G02': ('failed', 3, 'w04', '08:50', '09:35'),
?                    ^                      ^^

+  'G02': ('failed', 1, 'w04', '08:50', '09:00'),
?                    ^     ...
```

### B5: Wait loses whole days

- **Type:** timedelta-seconds
- **Symptom:** test_5_longest_wait fails: {'job': 'M04', 'minutes': 60} instead of {'job': 'M01', 'minutes': 2890}.
- **Location:** `batchsched/report.py` → `wait_minutes`
- **Why it fails:** `timedelta.seconds` is only the seconds part of the duration, not counting whole days. M01 was submitted on 09/29 and waited 2 days 10 minutes, but `.seconds` gives 600 s, so M04's 60 minutes looks like the longest wait.
- **Failing test:** `test_3_report.TestReport.test_5_longest_wait`
- **Unblocks:** test_5_longest_wait.

Fix:

```diff
-    return (started - job.submitted_at).seconds // 60
+    return int((started - job.submitted_at).total_seconds() // 60)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_5_longest_wait`):

```
AssertionError: {'job': 'M04', 'minutes': 60} != {'job': 'M01', 'minutes': 2890}
- {'job': 'M04', 'minutes': 60}
?            ^              ^

+ {'job': 'M01', 'minutes': 2890}
?            ^              ^^^
```

### B6: Inactive workers counted as slots

- **Type:** counting-wrong-subset
- **Symptom:** test_6_pool_capacity fails: slots {'cpu': 4, 'gpu': 2, 'io': 1, 'mem': 3}. Expected {'cpu': 2, 'gpu': 1, 'io': 1, 'mem': 2}.
- **Location:** `batchsched/pools.py` → `capacity`
- **Why it fails:** Slots are active workers only. capacity() counts every worker in the roster, including draining and offline ones, so the report shows cpu 4 / gpu 2 / mem 3 and halves cpu utilization. The scheduler is unaffected because PoolTable filters active workers itself.
- **Failing test:** `test_3_report.TestReport.test_6_pool_capacity`
- **Unblocks:** test_6_pool_capacity.

Fix:

```diff
-    return Counter(w.pool for w in workers)
+    return Counter(w.pool for w in workers if w.active)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_6_pool_capacity`):

```
AssertionError: {'cpu': 4, 'gpu': 2, 'io': 1, 'mem': 3} != {'cpu': 2, 'gpu': 1, 'io': 1, 'mem': 2}
- {'cpu': 4, 'gpu': 2, 'io': 1, 'mem': 3}
?         ^         ^                  ^

+ {'cpu': 2, 'gpu': 1, 'io': 1, 'mem': 2}
?         ^         ^                  ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `batchsched/timeutil.py` → `parse_duration`: The regex accepts a number with an optional h/m/s unit. `// 60` on seconds looks lossy, but every seconds value in the data is a whole number of minutes, and the spec says everything is in whole minutes. A bare number is minutes, as the README says.
- `batchsched/retry.py` → `backoff_delay`: Backoff is linear by spec (`retry_backoff × attempts made so far`), so `base * attempts` is right even though exponential backoff is what most people expect.
