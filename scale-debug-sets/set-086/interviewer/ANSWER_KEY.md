# set-086 answer key: Load balancer replay with health checks and sticky sessions

**Domain:** load_balancer  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_health.TestHealth.test_backends_in_rotation`
- `tests.test_1_health.TestHealth.test_final_state`
- `tests.test_1_health.TestHealth.test_transitions`
- `tests.test_2_routing.TestRouting.test_assignments`
- `tests.test_2_routing.TestRouting.test_opening_requests`
- `tests.test_2_routing.TestRouting.test_sessions`
- `tests.test_3_report.TestReport.test_failovers_and_rejections`
- `tests.test_3_report.TestReport.test_median_latency`
- `tests.test_3_report.TestReport.test_request_counts`
- `tests.test_3_report.TestReport.test_zones`

## Bugs (recommended order)

### B1: enabled=false backend joins the pool

- **Type:** bool-from-string
- **Symptom:** All three files fail. Test 1: b05 appears in final_state (down) with an extra [9500, 'b05', 'down'] transition. Test 2: R03 goes to b05, and the opening requests, assignments and sessions all shift. Test 3: b05 has 4 requests, zones are east 22 / west 8, and failovers is 2.
- **Location:** `lbreplay/loader.py` → `parse_flag`
- **Why it fails:** Any non-empty string is truthy, so b05's `false` reads as enabled. b05 takes traffic from the start, and its two failed checks (which are ignored for a disabled backend) now mark it down at 9.5 s.
- **Unblocks:** test_backends_in_rotation, the b05 transition in test_1, and the early routing in test_2.

Fix:

```diff
-    return bool(norm(value))
+    return norm(value) in YES
```

Observed with only this bug applied (`tests.test_1_health.TestHealth.test_backends_in_rotation`):

```
AssertionError: Lists differ: ['b01', 'b02', 'b03', 'b04', 'b05'] != ['b01', 'b02', 'b03', 'b04']

First list contains 1 additional elements.
First extra element 4:
'b05'

- ['b01', 'b02', 'b03', 'b04', 'b05']
?                            -------

+ ['b01', 'b02', 'b03', 'b04']
```

### B2: Fail streak not reset by a passing check

- **Type:** state-not-reset
- **Symptom:** Test 1: extra transitions [14000, 'b02', 'down'] and [18000, 'b02', 'healthy']. Test 2: requests around 14-18 s move off b02 (e.g. R20 -> b03) and erin ends on b01. Test 3: counts b01 15 / b02 7 / b03 2 / b04 6, failovers 2.
- **Location:** `lbreplay/health.py` → `HealthTracker.observe`
- **Why it fails:** FALL counts consecutive failures. Without the reset, b02's fail-pass-fail at 10/12/14 s adds up to 2 and marks it down from 14 s to 18 s, so mid-run requests move to other backends.
- **Unblocks:** test_transitions and test_final_state (b02), and the 14-18 s routing.

Fix:

```diff
             if check.ok:
+                self.fails[bid] = 0
                 return
```

Observed with only this bug applied (`tests.test_1_health.TestHealth.test_transitions`):

```
AssertionError: Lists differ: [[14000, 'b02', 'down'], [18000, 'b02', 'he[54 chars]hy']] != [[21000, 'b03', 'down'], [32000, 'b03', 'healthy']]

First differing element 0:
[14000, 'b02', 'down']
[21000, 'b03', 'down']

First list contains 2 additional elements.
First extra element 2:
[21000, 'b03', 'down']

+ [[21000, 'b03', 'down'], [32000, 'b03', 'healthy']]
- [[14000, 'b02', 'down'],
-  [18000, ...
```

### B3: Sticky check compares an Enum to a string

- **Type:** enum-vs-string
- **Symptom:** Tests 2 and 3 fail; Test 1 passes. Sticky sessions are never reused: from R07 on, assignments follow pure round robin, dave ends on b01 and erin on b04, and failovers is 7 instead of 1.
- **Location:** `lbreplay/replay.py` → `Replay.route`
- **Why it fails:** `BackendState` is a plain Enum, so `BackendState.HEALTHY == "healthy"` is always False. Sticky sessions are never reused, every repeat request goes through round robin, and most of them count as failovers.
- **Unblocks:** Most of test_2 and the failover count in test_3. It also exposes B4.

Fix:

```diff
-        if previous is not None and self.health.state[previous] == "healthy":
+        if previous is not None and self.health.state[previous] is BackendState.HEALTHY:
```

Observed with only this bug applied (`tests.test_2_routing.TestRouting.test_assignments`):

```
AssertionError: {'R01[85 chars]: 'b02', 'R08': 'b01', 'R09': 'b02', 'R10': 'b[279 chars]b01'} != {'R01[85 chars]: 'b01', 'R08': 'b02', 'R09': 'b02', 'R10': 'b[279 chars]b04'}
  {'R01': 'b01',
   'R02': 'b02',
   'R03': 'b03',
   'R04': 'b01',
   'R05': 'b04',
   'R06': 'b01',
-  'R07': 'b02',
?            ^

+  'R07': 'b01',
?            ^

-  'R08': 'b01',
?            ^

+  'R08': 'b02',
?       ...
```

### B4: Sticky reuse allowed at max_conns

- **Type:** off-by-one
- **Symptom:** Hidden while B3 is present. Once B3 is fixed: R07 goes to b03 (expected b01) and the rotation shifts after that. Test 3 counts become b01 13 / b02 8 / b03 4 / b04 5, and zones east 21 / west 9.
- **Location:** `lbreplay/sessions.py` → `has_room`
- **Why it fails:** A backend with max_conns 1 that already has 1 request in flight is full. With `<=`, carol's R07 stays on b03 while R03 is still running, so b03 serves two requests at once and the round-robin sequence shifts from there. This branch can't be reached while B3 stops every sticky reuse.
- **Unblocks:** R07 and the later assignments in test_2, plus the request counts, medians and zones in test_3.
- **Masked:** invisible until B3 is fixed (identical test output either way).

Fix:

```diff
-    return active <= backend.max_conns
+    return active < backend.max_conns
```

Observed with only this bug applied (`tests.test_2_routing.TestRouting.test_assignments`):

```
AssertionError: {'R01[85 chars]: 'b03', 'R08': 'b01', 'R09': 'b02', 'R10': 'b[279 chars]b04'} != {'R01[85 chars]: 'b01', 'R08': 'b02', 'R09': 'b02', 'R10': 'b[279 chars]b04'}
  {'R01': 'b01',
   'R02': 'b02',
   'R03': 'b03',
   'R04': 'b01',
   'R05': 'b04',
   'R06': 'b01',
-  'R07': 'b03',
?            ^

+  'R07': 'b01',
?            ^

-  'R08': 'b01',
?            ^

+  'R08': 'b02',
?       ...
```

### B5: Median takes the upper middle value

- **Type:** off-by-one
- **Symptom:** Only test_3 test_median_latency fails: b01 p50 is 320 instead of 300. Every other backend is right.
- **Location:** `lbreplay/metrics.py` → `p50`
- **Why it fails:** The nearest-rank median of n values is the ceil(n/2)-th value (1-based). `n // 2` as a 0-based index matches only for odd n. For even n it takes the next value up, so b01 (14 requests) reports 320 instead of 300.
- **Unblocks:** test_median_latency.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-    return ordered[len(ordered) // 2]
+    return ordered[math.ceil(0.5 * len(ordered)) - 1]
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_median_latency`):

```
AssertionError: {'b01': 320, 'b02': 300, 'b03': 2500, 'b04': 350} != {'b01': 300, 'b02': 300, 'b03': 2500, 'b04': 350}
- {'b01': 320, 'b02': 300, 'b03': 2500, 'b04': 350}
?          ^

+ {'b01': 300, 'b02': 300, 'b03': 2500, 'b04': 350}
?          ^
```

### B6: Counter.update on a zone string

- **Type:** counter-misuse
- **Symptom:** Only test_3 test_zones fails: zones is {'a': 24, 'e': 30, 's': 30, 't': 30, 'w': 6} instead of {'east': 24, 'west': 6}.
- **Location:** `lbreplay/report.py` → `zone_totals`
- **Why it fails:** `Counter.update` with a string counts its characters, so each request adds 1 to 'e', 'a', 's', 't' (or 'w', 'e', 's', 't') instead of 1 to the zone.
- **Unblocks:** test_zones.
- **Masked:** only surfaces in test_3_report.

Fix:

```diff
-            zones.update(backends[bid].zone)
+            zones[backends[bid].zone] += 1
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_zones`):

```
AssertionError: {'a': 24, 'e': 30, 's': 30, 't': 30, 'w': 6} != {'east': 24, 'west': 6}
- {'a': 24, 'e': 30, 's': 30, 't': 30, 'w': 6}
+ {'east': 24, 'west': 6}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `lbreplay/loader.py` → `parse_offset`: A bare number is milliseconds and `s` multiplies by 1000, exactly as the README lists. `int(round(...))` avoids float truncation for values like 1.5s. It looks like a classic ms/s trap, but every format in the data is handled right.
- `lbreplay/balancer.py` → `pick`: This is the nginx smooth weighted round robin: add each eligible backend's weight, pick the highest current value (lowest id on ties), then subtract the total eligible weight from the winner. Subtracting the total, rather than the weight, is what keeps the sequence smooth.
