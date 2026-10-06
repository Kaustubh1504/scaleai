# set-016 answer key: Nightly job scheduler: rounds, retries and skip cascade

**Domain:** job_scheduler  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_schedule.TestSchedule.test_all_rounds`
- `tests.test_1_schedule.TestSchedule.test_disabled_jobs_never_run`
- `tests.test_1_schedule.TestSchedule.test_first_round`
- `tests.test_2_outcomes.TestOutcomes.test_all_jobs`
- `tests.test_2_outcomes.TestOutcomes.test_attempts`
- `tests.test_2_outcomes.TestOutcomes.test_dead_jobs`
- `tests.test_2_outcomes.TestOutcomes.test_dependents_of_dead_jobs_skipped`
- `tests.test_3_summary.TestSummary.test_busy_minutes`
- `tests.test_3_summary.TestSummary.test_counts`
- `tests.test_3_summary.TestSummary.test_mean_attempts`
- `tests.test_3_summary.TestSummary.test_total_attempts`

## Bugs (recommended order)

### B1: Blank depends_on becomes a dependency on ""

- **Type:** empty-split
- **Symptom:** Every test file fails. Test 1: rounds is [] (test_first_round raises IndexError). Test 2: every job is pending with 0 attempts, no dead jobs, J09/J10 pending. Test 3: counts show pending 12, total_attempts 0, mean_attempts None, busy_minutes 0.0.
- **Location:** `nightshift/utils.py` → `split_ids`
- **Why it fails:** `"".split(";")` returns `[""]`, not `[]`. Every job with a blank depends_on now waits for a job with id "", which never succeeds, so no root job is ever ready and nothing runs.
- **Unblocks:** Test 1 (rounds appear at all) and most of Test 2.

Fix:

```diff
-    return [norm_id(part) for part in clean(text).split(sep)]
+    return [norm_id(part) for part in clean(text).split(sep) if part.strip()]
```

Observed with only this bug applied (`tests.test_1_schedule.TestSchedule.test_all_rounds`):

```
AssertionError: Lists differ: [] != [['J05', 'J02'], ['J01', 'J03'], ['J04', '[58 chars]14']]

Second list contains 7 additional elements.
First extra element 0:
['J05', 'J02']

- []
+ [['J05', 'J02'],
+  ['J01', 'J03'],
+  ['J04', 'J03'],
+  ['J06', 'J08'],
+  ['J08', 'J07'],
+  ['J07', 'J11'],
+  ['J14']]
```

### B2: "false"/"no" parsed as enabled

- **Type:** bool-from-string
- **Symptom:** Test 1: disabled J12 and J13 are scheduled (first round ['J05', 'J12'], then J13) and appear in the jobs table. Test 2: finished rounds shift by one and J12/J13 have 1 attempt each. Test 3: succeeded 10, total_attempts 15, mean_attempts 1.25, busy_minutes 86.0.
- **Location:** `nightshift/utils.py` → `parse_bool`
- **Why it fails:** bool() of any non-empty string is True, so `false` and `no` both count as enabled and the disabled jobs J12/J13 get scheduled and take worker slots.
- **Unblocks:** Test 1 disabled-jobs check and the round layout.

Fix:

```diff
-    return bool(text)
+    return text.lower() in TRUTHY
```

Observed with only this bug applied (`tests.test_1_schedule.TestSchedule.test_all_rounds`):

```
AssertionError: Lists differ: [['J05', 'J12'], ['J13', 'J02'], ['J01', 'J03'], ['J[64 chars]14']] != [['J05', 'J02'], ['J01', 'J03'], ['J04', 'J03'], ['J[48 chars]14']]

First differing element 0:
['J05', 'J12']
['J05', 'J02']

First list contains 1 additional elements.
First extra element 7:
['J14']

- [['J05', 'J12'],
?            ^

+ [['J05', 'J02'],
?            ^

-  ['J13', 'J02'],
   ['J01 ...
```

### B3: Priority sorted least urgent first

- **Type:** sort-direction
- **Symptom:** Test 1: first round is ['J03', 'J02'] instead of ['J05', 'J02'] and the later rounds are reshuffled. Test 2: test_all_jobs fails on finished_round values (e.g. J03 finishes in round 2, J04 in round 5). Test 3 still passes.
- **Location:** `nightshift/scheduler.py` → `ready_jobs`
- **Why it fails:** The README says a higher priority number is more urgent, but the sort key is ascending, so the least urgent ready jobs take the worker slots first. The comment above still says 'most urgent first'.
- **Unblocks:** Test 1 rounds and the finished_round values in Test 2.

Fix:

```diff
-    return sorted(ready, key=lambda j: (j.priority, j.submitted_at, j.job_id))
+    return sorted(ready, key=lambda j: (-j.priority, j.submitted_at, j.job_id))
```

Observed with only this bug applied (`tests.test_1_schedule.TestSchedule.test_all_rounds`):

```
AssertionError: Lists differ: [['J03', 'J02'], ['J03', 'J01'], ['J07', 'J08'[56 chars]14']] != [['J05', 'J02'], ['J01', 'J03'], ['J04', 'J03'[54 chars]14']]

First differing element 0:
['J03', 'J02']
['J05', 'J02']

First list contains 1 additional elements.
First extra element 7:
['J14']

- [['J03', 'J02'],
?      ^

+ [['J05', 'J02'],
?      ^

-  ['J03', 'J01'],
-  ['J07', 'J08'],
?      ^      ...
```

### B4: One retry too many

- **Type:** retry-off-by-one
- **Symptom:** Test 1: an extra round ['J09', 'J10'] appears. Test 2: only J05 is dead (with 2 attempts), J07 succeeds on a third attempt, and J09/J10 run and succeed instead of being skipped. Test 3: succeeded 11, dead 1, skipped 0, total_attempts 17, mean 1.42, busy_minutes 114.7.
- **Location:** `nightshift/models.py` → `Job.can_retry`
- **Why it fails:** retries_left is already the number of retries still allowed after this attempt; `>= 0` lets a job with zero retries left run once more, so jobs get max_retries + 2 attempts. J07 then succeeds on its third attempt and never dies.
- **Unblocks:** Test 2 dead jobs and attempts; exposes B5.

Fix:

```diff
-        return self.retries_left >= 0
+        return self.retries_left > 0
```

Observed with only this bug applied (`tests.test_1_schedule.TestSchedule.test_all_rounds`):

```
AssertionError: Lists differ: [['J05', 'J02'], ['J05', 'J01'], ['J04', 'J03'], ['J06', 'J03'[70 chars]14']] != [['J05', 'J02'], ['J01', 'J03'], ['J04', 'J03'], ['J06', 'J08'[38 chars]14']]

First differing element 1:
['J05', 'J01']
['J01', 'J03']

First list contains 2 additional elements.
First extra element 7:
['J09', 'J10']

  [['J05', 'J02'],
-  ['J05', 'J01'],
+  ['J01', 'J03'],
   ['J04', 'J ...
```

### B5: Skip cascade stops after the first dependent

- **Type:** early-return
- **Symptom:** Only visible after B4 is fixed. Test 2: J10 stays pending instead of skipped (J09 is skipped). Test 3: counts show skipped 1 and pending 1. Test 1 is unaffected.
- **Location:** `nightshift/scheduler.py` → `skip_dependents`
- **Why it fails:** The return inside the loop ends the scan after the first dependent, so when J07 dies only J09 is skipped and J10 is left pending forever.
- **Unblocks:** Test 2 skipped jobs and the pending count in Test 3.
- **Masked:** invisible until B4 is fixed (identical test output either way).

Fix:

```diff
             skipped.append(job.job_id)
-            return skipped + skip_dependents(jobs, job.job_id)
+            skipped.extend(skip_dependents(jobs, job.job_id))
```

Observed with only this bug applied (`tests.test_2_outcomes.TestOutcomes.test_all_jobs`):

```
AssertionError: {'J01[613 chars]s': 'pending', 'attempts': 0, 'finished_round'[139 chars]: 7}} != {'J01[613 chars]s': 'skipped', 'attempts': 0, 'finished_round'[139 chars]: 7}}
  {'J01': {'attempts': 1, 'finished_round': 2, 'status': 'succeeded'},
   'J02': {'attempts': 1, 'finished_round': 1, 'status': 'succeeded'},
   'J03': {'attempts': 2, 'finished_round': 3, 'status': 'succeeded'},
   'J04':  ...
```

### B6: Mean attempts floored

- **Type:** integer-division
- **Symptom:** Test 3 only: mean_attempts is 1 instead of 1.3.
- **Location:** `nightshift/reports.py` → `summarize`
- **Why it fails:** `//` floors 13 ÷ 10 to 1 before round() sees it, so the 2-decimal rounding never has anything to round.
- **Unblocks:** Test 3.
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-        "mean_attempts": round(total_attempts // len(ran), 2) if ran else None,
+        "mean_attempts": round(total_attempts / len(ran), 2) if ran else None,
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_mean_attempts`):

```
AssertionError: 1 != 1.3
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `nightshift/utils.py` → `parse_timestamp`: The slash format is `%d/%m/%Y`, which looks swapped to anyone used to US dates, but the README says the slash format is day/month/year. It covers exactly the three listed formats.
