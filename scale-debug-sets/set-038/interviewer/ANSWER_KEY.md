# set-038 answer key: Load balancer replay: health probes, weighted least-connections

**Domain:** load_balancer  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_routing.TestRouting.test_api_routes`
- `tests.test_1_routing.TestRouting.test_batch_routes`
- `tests.test_1_routing.TestRouting.test_static_routes`
- `tests.test_2_backends.TestBackends.test_busy_ms`
- `tests.test_2_backends.TestBackends.test_peak_connections`
- `tests.test_2_backends.TestBackends.test_served`
- `tests.test_3_report.TestReport.test_by_pool`
- `tests.test_3_report.TestReport.test_utilization`

## Bugs (recommended order)

### B1: Health strings read with bool()

- **Type:** bool-from-string
- **Symptom:** Test 1 test_api_routes: R14 and R19 go to api-3 instead of api-1, although api-3 failed two probes. Test 2: api-1 served 4 (want 6), api-3 served 5 (want 3), api-3 peak 2; busy_ms shifts by 650. Test 3 utilization: api-1 0.22, api-3 0.201.
- **Location:** `lbsim/loader.py` → `load_probes`
- **Why it fails:** bool() of any non-empty string is True, so 'false', 'no' and '0' probes all count as healthy. api-3 never goes down after its two failed probes, and keeps taking traffic.
- **Unblocks:** Test 1 api routes (R14, R19), Test 2 api-1/api-3 counts, Test 3 utilization. Exposes B3.

Fix:

```diff
-healthy=bool(row["healthy"].strip()),
+healthy=parse_bool(row["healthy"]),
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_api_routes`):

```
AssertionError: {'R01[131 chars]'api-3', 'R18': 'api-2', 'R19': 'api-3', 'R21'[37 chars]i-3'} != {'R01[131 chars]'api-1', 'R18': 'api-2', 'R19': 'api-1', 'R21'[37 chars]i-3'}
  {'R01': 'api-1',
   'R02': 'api-2',
   'R03': 'api-3',
   'R04': 'api-1',
   'R09': 'api-2',
   'R10': 'api-3',
   'R12': 'api-1',
   'R13': 'api-2',
-  'R14': 'api-3',
?              ^

+  'R14': 'api-1',
?              ^
 ...
```

### B2: Load ratio uses floor division

- **Type:** integer-division
- **Symptom:** Fails all three files widely. Test 1: R02 goes to api-1, R03 to api-2, R04 to api-3 ..., and every batch request lands on bt-1. Test 2: api-1 served 9, bt-3 served 0 (bt-3 disappears from peak/busy). Test 3 utilization changes and bt-3 is missing.
- **Location:** `lbsim/balancer.py` → `load_of`
- **Why it fails:** 1 // 2 is 0, so a weight-2 backend with one connection looks idle and ties with empty backends; the higher-weight tie-break then sends it more traffic. bt-1 (weight 3) takes every batch request.
- **Unblocks:** Most of Test 1 api and batch routes, Test 2 served/busy, Test 3 utilization.

Fix:

```diff
-    return len(backend.active) // backend.weight
+    return len(backend.active) / backend.weight
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_api_routes`):

```
AssertionError: {'R01[19 chars]'api-1', 'R03': 'api-2', 'R04': 'api-3', 'R09'[149 chars]i-1'} != {'R01[19 chars]'api-2', 'R03': 'api-3', 'R04': 'api-1', 'R09'[149 chars]i-3'}
Diff is 926 characters long. Set self.maxDiff to None to see it.
```

### B3: Failure count not reset by a healthy probe

- **Type:** state-not-reset
- **Symptom:** Only visible once B1 is fixed. Test 1: R18 is rejected (None) instead of going to api-2. Test 2: api-2 served 4 / peak 1 / busy 1400. Test 3: totals (25, 2, 0.074) and by_pool api 13.
- **Location:** `lbsim/health.py` → `apply_probe`
- **Why it fails:** api-2 goes fail (900), ok (1150), fail (1300). Without the reset the second failure is counted as consecutive, so api-2 goes down at 1300 and R18 is rejected. While B1 is present no probe ever fails, so the counter never moves and this is invisible.
- **Unblocks:** Test 1 R18, Test 2 api-2, Test 3 totals.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
+        backend.fails = 0
         backend.healthy = True
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_api_routes`):

```
AssertionError: {'R01[142 chars]18': None, 'R19': 'api-1', 'R21': 'api-1', 'R2[23 chars]i-3'} != {'R01[142 chars]18': 'api-2', 'R19': 'api-1', 'R21': 'api-1', [26 chars]i-3'}
  {'R01': 'api-1',
   'R02': 'api-2',
   'R03': 'api-3',
   'R04': 'api-1',
   'R09': 'api-2',
   'R10': 'api-3',
   'R12': 'api-1',
   'R13': 'api-2',
   'R14': 'api-1',
-  'R18': None,
+  'R18': 'api-2',
   'R19': 'api-1',
 ...
```

### B4: Connections ending exactly at arrival kept open

- **Type:** time-window-boundary
- **Symptom:** Test 1: R15 goes to st-2, R16 is rejected and R27 gets st-1; R09/R10/R22/R26 shift and R19 is rejected. Test 2: api-1 served 7, api-3 served 1. Test 3: totals (25, 2, 0.074), by_pool api 13, utilization changes.
- **Location:** `lbsim/balancer.py` → `release_finished`
- **Why it fails:** The README closes connections whose end is <= t. Keeping end == t open makes st-1 (busy until exactly 2000) look full when R15 and R16 arrive at 2000, and does the same to api backends at 600, 700 and 1600.
- **Unblocks:** Test 1 static and api routes, Test 2, Test 3 totals.

Fix:

```diff
-if end >= now_ms]
+if end > now_ms]
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_api_routes`):

```
AssertionError: {'R01[67 chars]'api-1', 'R10': 'api-2', 'R12': 'api-1', 'R13'[98 chars]i-2'} != {'R01[67 chars]'api-2', 'R10': 'api-3', 'R12': 'api-1', 'R13'[101 chars]i-3'}
  {'R01': 'api-1',
   'R02': 'api-2',
   'R03': 'api-3',
   'R04': 'api-1',
-  'R09': 'api-1',
?              ^

+  'R09': 'api-2',
?              ^

-  'R10': 'api-2',
?              ^

+  'R10': 'api-3',
?              ^

   ...
```

### B5: Zero-length requests given the default duration

- **Type:** falsy-zero
- **Symptom:** Test 1 test_batch_routes: R07 goes to bt-1 and R11 to bt-3 (swapped), and R24/R25 swap too. Test 2 busy_ms: bt-1 3000, bt-3 650. Test 3 utilization bt-1 0.244, bt-3 0.159.
- **Location:** `lbsim/loader.py` → `load_requests`
- **Why it fails:** parse_ms returns 0 for '0', and `or` replaces it with 100. R06 then holds bt-1 until 500 instead of closing at 400, so R11 and R07 swap backends; R24 and R25 change too.
- **Unblocks:** Test 1 batch routes, Test 2 bt-1/bt-3 busy_ms, Test 3 utilization.

Fix:

```diff
-duration_ms=parse_ms(row["duration"]) or DEFAULT_DURATION_MS,
+duration_ms=parse_ms(row["duration"], DEFAULT_DURATION_MS),
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_batch_routes`):

```
AssertionError: {'R06[17 chars] 'bt-1', 'R11': 'bt-3', 'R17': 'bt-1', 'R20': [32 chars]t-3'} != {'R06[17 chars] 'bt-3', 'R11': 'bt-1', 'R17': 'bt-1', 'R20': [32 chars]t-1'}
  {'R06': 'bt-1',
-  'R07': 'bt-1',
?             ^

+  'R07': 'bt-3',
?             ^

-  'R11': 'bt-3',
?             ^

+  'R11': 'bt-1',
?             ^

   'R17': 'bt-1',
   'R20': 'bt-3',
-  'R24': 'bt-1',
?             ^ ...
```

### B6: by_pool counts rejected requests

- **Type:** counting-wrong-subset
- **Symptom:** Test 3 test_by_pool only: static is 6 instead of 5 (the rejected R27 is counted). routed is still 26.
- **Location:** `lbsim/reports.py` → `summarize`
- **Why it fails:** The README counts routed requests per pool. Counting all requests includes the rejected R27, so static shows 6 instead of 5.
- **Unblocks:** Test 3 test_by_pool.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-Counter(r.pool for r in requests)
+Counter(r.pool for r in routed)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_by_pool`):

```
AssertionError: {'api': 14, 'batch': 7, 'static': 6} != {'api': 14, 'batch': 7, 'static': 5}
- {'api': 14, 'batch': 7, 'static': 6}
?                                   ^

+ {'api': 14, 'batch': 7, 'static': 5}
?                                   ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `lbsim/balancer.py` → `pick`: Checking the sticky id before `if not options` looks out of order, but the loop over an empty list simply does nothing, and the sticky backend is only honoured if it is in the candidate list (enabled, healthy, below its cap). The key (load, -weight, id) is exactly the README order: lowest load, then higher weight, then id.
