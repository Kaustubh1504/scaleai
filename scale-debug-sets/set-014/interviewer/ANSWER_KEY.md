# set-014 answer key: Weighted least-connections balancer replay

**Domain:** load_balancer  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_health.TestHealth.test_1_worker_states` | B1 Draining check compares an Enum to a string |
| `test_1_health.TestHealth.test_2_availability` | B2 Timeouts counted as passing probes |
| `test_2_routing.TestRouting.test_3_assignments` | B3 Weight dropped from the routing tie-break |
| `test_2_routing.TestRouting.test_4_peak_in_flight` | B4 Starts counted before ends at the same instant |
| `test_3_report.TestReport.test_5_zone_served` | B5 served list shared by every worker |
| `test_3_report.TestReport.test_6_zone_mean_duration` | B6 Mean duration uses floor division |

## Failing pattern with all bugs present

- `tests.test_1_health.TestHealth.test_1_worker_states`
- `tests.test_1_health.TestHealth.test_2_availability`
- `tests.test_2_routing.TestRouting.test_3_assignments`
- `tests.test_2_routing.TestRouting.test_4_peak_in_flight`
- `tests.test_3_report.TestReport.test_5_zone_served`
- `tests.test_3_report.TestReport.test_6_zone_mean_duration`

## Bugs (recommended order)

### B1: Draining check compares an Enum to a string

- **Type:** enum-vs-string
- **Symptom:** test_1_worker_states fails: W-08 is 'down' instead of 'draining'. All other workers match, and routing is unchanged because neither state is eligible.
- **Location:** `lbsim/health.py` → `apply_probes`
- **Why it fails:** worker.state is a State member, and State.DRAINING == "draining" is False (a plain Enum never equals its value). The skip never fires, so W-08's three failed probes take it down.
- **Failing test:** `test_1_health.TestHealth.test_1_worker_states`
- **Unblocks:** test_1_worker_states.

Fix:

```diff
-        if worker.state == "draining":
+        if worker.state is State.DRAINING:
```

Observed with only this bug applied (`tests.test_1_health.TestHealth.test_1_worker_states`):

```
AssertionError: {'W-0[80 chars], 'W-07': 'up', 'W-08': 'down', 'W-09': 'up', 'W-10': 'up'} != {'W-0[80 chars], 'W-07': 'up', 'W-08': 'draining', 'W-09': 'up', 'W-10': 'up'}
  {'W-01': 'up',
   'W-02': 'down',
   'W-03': 'up',
   'W-04': 'up',
   'W-05': 'up',
   'W-06': 'up',
   'W-07': 'up',
-  'W-08': 'down',
?            ^^

+  'W-08': 'draining',
?            ^^^ +++

   'W-09': 'up',
   'W-10 ...
```

### B2: Timeouts counted as passing probes

- **Type:** counting-wrong-subset
- **Symptom:** test_2_availability fails: W-04 and W-08 show 1.0 instead of 0.0. Their only probe in the window is a timeout.
- **Location:** `lbsim/health.py` → `availability`
- **Why it fails:** Only `fail` is excluded, so `timeout` probes are counted as passing. The spec, and is_failure() which the state machine uses, treat timeouts as failures.
- **Failing test:** `test_1_health.TestHealth.test_2_availability`
- **Unblocks:** test_2_availability.

Fix:

```diff
-            passing = sum(1 for p in recent if p.result != "fail")
+            passing = sum(1 for p in recent if not is_failure(p))
```

Observed with only this bug applied (`tests.test_1_health.TestHealth.test_2_availability`):

```
AssertionError: {'W-0[39 chars]04': 1.0, 'W-05': None, 'W-06': 1.0, 'W-07': 1[37 chars] 0.0} != {'W-0[39 chars]04': 0.0, 'W-05': None, 'W-06': 1.0, 'W-07': 1[37 chars] 0.0}
  {'W-01': 1.0,
   'W-02': 0.0,
   'W-03': None,
-  'W-04': 1.0,
?          ^

+  'W-04': 0.0,
?          ^

   'W-05': None,
   'W-06': 1.0,
   'W-07': 1.0,
-  'W-08': 1.0,
?          ^

+  'W-08': 0.0,
?          ^

   'W-09' ...
```

### B3: Weight dropped from the routing tie-break

- **Type:** wrong-tie-break
- **Symptom:** test_3_assignments fails: R01 goes to W-01 instead of W-04, R02 to W-03, R03 to W-05, and so on. Every move stays inside the same zone, so peak and zone totals don't change.
- **Location:** `lbsim/router.py` → `pick_worker`
- **Why it fails:** When loads are equal (for example all idle), the spec gives the request to the higher-weight worker. Without -w.weight in the key, the lowest id wins, so R01 goes to W-01 instead of W-04 and the following choices shift.
- **Failing test:** `test_2_routing.TestRouting.test_3_assignments`
- **Unblocks:** test_3_assignments.

Fix:

```diff
-(len(w.active) / w.weight, w.worker_id)
+(len(w.active) / w.weight, -w.weight, w.worker_id)
```

Observed with only this bug applied (`tests.test_2_routing.TestRouting.test_3_assignments`):

```
AssertionError: {'R01': 'W-01', 'R02': 'W-03', 'R03': 'W-05', 'R04': [227 chars]-09'} != {'R01': 'W-04', 'R02': 'W-01', 'R03': 'W-06', 'R04': [227 chars]-09'}
- {'R01': 'W-01',
?             ^

+ {'R01': 'W-04',
?             ^

-  'R02': 'W-03',
?             ^

+  'R02': 'W-01',
?             ^

-  'R03': 'W-05',
?             ^

+  'R03': 'W-06',
?             ^

   'R04': 'W-09',
-  'R05': 'W- ...
```

### B4: Starts counted before ends at the same instant

- **Type:** time-window-boundary
- **Symptom:** test_4_peak_in_flight fails: 7 instead of 5.
- **Location:** `lbsim/reports.py` → `peak_in_flight`
- **Why it fails:** At equal timestamps the -1 (end) events must come before the +1 (start) events, because a request ending at t does not overlap one starting at t. Sorting by -delta puts starts first and counts back-to-back requests as overlapping.
- **Failing test:** `test_2_routing.TestRouting.test_4_peak_in_flight`
- **Unblocks:** test_4_peak_in_flight.

Fix:

```diff
-events.sort(key=lambda e: (e[0], -e[1]))
+events.sort(key=lambda e: (e[0], e[1]))
```

Observed with only this bug applied (`tests.test_2_routing.TestRouting.test_4_peak_in_flight`):

```
AssertionError: 7 != 5
```

### B5: served list shared by every worker

- **Type:** shared-class-attribute
- **Symptom:** test_5_zone_served fails: every zone shows a multiple of 19 (e.g. {'ap-south': 171, 'eu-west': 171, 'us-east': 228} in a full-suite run, or 57/57/76 when test_3 runs alone) instead of 6/5/8.
- **Location:** `lbsim/models.py` → `Worker`
- **Why it fails:** `served = []` at class level is one list shared by every Worker, and served.append() mutates it in place. Every worker holds every routed request, and the list keeps growing each time build_report runs in the same process, so each zone sums a multiple of 19.
- **Failing test:** `test_3_report.TestReport.test_5_zone_served`
- **Unblocks:** test_5_zone_served.

Fix:

```diff
     """A backend in the pool. `active` holds the end times of its open connections."""
 
-    served = []
-
     def __init__(self, worker_id, zone, weight, max_conns, state):
+        self.served = []
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_5_zone_served`):

```
AssertionError: {'ap-south': 171, 'eu-west': 171, 'us-east': 228} != {'ap-south': 6, 'eu-west': 5, 'us-east': 8}
- {'ap-south': 171, 'eu-west': 171, 'us-east': 228}
?              ^^^             ^^^             --

+ {'ap-south': 6, 'eu-west': 5, 'us-east': 8}
?              ^             ^
```

### B6: Mean duration uses floor division

- **Type:** integer-division
- **Symptom:** test_6_zone_mean_duration fails: {'ap-south': 1316, 'eu-west': 1060, 'us-east': 1087} instead of 1316.7 / 1060.0 / 1087.5.
- **Location:** `lbsim/reports.py` → `zone_summary`
- **Why it fails:** `//` floors the mean to a whole number before rounding, so 7900/6 becomes 1316 and 8700/8 becomes 1087.
- **Failing test:** `test_3_report.TestReport.test_6_zone_mean_duration`
- **Unblocks:** test_6_zone_mean_duration.

Fix:

```diff
-round(sum(durations[zone]) // len(durations[zone]), 1)
+round(sum(durations[zone]) / len(durations[zone]), 1)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_6_zone_mean_duration`):

```
AssertionError: {'ap-south': 1316, 'eu-west': 1060, 'us-east': 1087} != {'ap-south': 1316.7, 'eu-west': 1060.0, 'us-east': 1087.5}
- {'ap-south': 1316, 'eu-west': 1060, 'us-east': 1087}
+ {'ap-south': 1316.7, 'eu-west': 1060.0, 'us-east': 1087.5}
?                  ++                 ++                 ++
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `lbsim/router.py` → `release_finished`: `end > now` keeps only connections that are still open. A connection that ends exactly when a request arrives is closed for that request, as README rule 6 says, so `>` (not `>=`) is right.
- `lbsim/loader.py` → `parse_time`: It covers exactly the three timestamp formats the README lists, with month/day order for the slash format.
