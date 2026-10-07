# set-062 answer key: Zone-local least-inflight replay

**Domain:** load_balancer  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_routing.TestRouting.test_1_east_assignments` | B1 Degraded check compares the enum to a string |
| `test_1_routing.TestRouting.test_2_west_assignments` | B2 Request ending at the arrival time still counted as running |
| `test_2_workers.TestWorkerStats.test_3_central_utilisation` | B3 Utilisation rounded before scaling to a percentage |
| `test_2_workers.TestWorkerStats.test_4_central_peak_inflight` | B4 Peak counter carried across workers |
| `test_3_summary.TestSummary.test_5_rejected` | B5 max_inflight 0 replaced by the default |
| `test_3_summary.TestSummary.test_6_out_of_rotation` | B6 Out-of-rotation filter always true |

## Failing pattern with all bugs present

- `tests.test_1_routing.TestRouting.test_1_east_assignments`
- `tests.test_1_routing.TestRouting.test_2_west_assignments`
- `tests.test_2_workers.TestWorkerStats.test_3_central_utilisation`
- `tests.test_2_workers.TestWorkerStats.test_4_central_peak_inflight`
- `tests.test_3_summary.TestSummary.test_5_rejected`
- `tests.test_3_summary.TestSummary.test_6_out_of_rotation`

## Bugs (recommended order)

### B1: Degraded check compares the enum to a string

- **Type:** enum-vs-string
- **Symptom:** Test 1 test_1_east_assignments: e05 goes to east-2 instead of east-1, and e06 to east-1 instead of east-2. Every other zone is unaffected.
- **Location:** `relaymesh/router.py` → `effective_weight`
- **Why it fails:** Worker states are WorkerState members, and a plain Enum never equals its value string. So the check is never true, east-2 keeps its full weight while degraded, and it wins ties it should lose.
- **Failing test:** `test_1_routing.TestRouting.test_1_east_assignments`
- **Unblocks:** test_1_east_assignments.

Fix:

```diff
# relaymesh/router.py
-    if worker.state == "degraded":
+    if worker.state is WorkerState.DEGRADED:

# relaymesh/router.py
-from relaymesh.models import ACCEPTING
+from relaymesh.models import ACCEPTING, WorkerState
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_1_east_assignments`):

```
AssertionError: {'e01[68 chars]': 'east-2', 'e06': 'east-1', 'e07': 'east-1', 'e08': 'east-2'} != {'e01[68 chars]': 'east-1', 'e06': 'east-2', 'e07': 'east-1', 'e08': 'east-2'}
  {'e01': 'east-1',
   'e02': 'east-2',
   'e03': 'east-3',
   'e04': 'east-1',
-  'e05': 'east-2',
?               ^

+  'e05': 'east-1',
?               ^

-  'e06': 'east-1',
?               ^

+  'e06': 'east-2',
?      ...
```

### B2: Request ending at the arrival time still counted as running

- **Type:** off-by-one
- **Symptom:** Test 1 test_2_west_assignments: w02 goes to west-2 instead of west-1, and w03 to west-1 instead of west-2.
- **Location:** `relaymesh/router.py` → `release_finished`
- **Why it fails:** Rule 2 says a request ending at or before the new arrival has finished. Keeping `end >= now` leaves w01 (ends 12:00:02) on west-1 when w02 arrives at exactly 12:00:02, so w02 goes to west-2 and w03 flips too.
- **Failing test:** `test_1_routing.TestRouting.test_2_west_assignments`
- **Unblocks:** test_2_west_assignments.

Fix:

```diff
-    w.inflight = [end for end in w.inflight if end >= now_ms]
+    w.inflight = [end for end in w.inflight if end > now_ms]
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_2_west_assignments`):

```
AssertionError: {'w01[21 chars]west-2', 'w03': 'west-1', 'w04': 'west-1', 'w0[25 chars]t-1'} != {'w01[21 chars]west-1', 'w03': 'west-2', 'w04': 'west-1', 'w0[25 chars]t-1'}
  {'w01': 'west-1',
-  'w02': 'west-2',
?               ^

+  'w02': 'west-1',
?               ^

-  'w03': 'west-1',
?               ^

+  'w03': 'west-2',
?               ^

   'w04': 'west-1',
   'w05': 'west-1',
   'w06': ' ...
```

### B3: Utilisation rounded before scaling to a percentage

- **Type:** float-rounding
- **Symptom:** Test 2 test_3_central_utilisation: cen-1 shows 114.99999999999999 instead of 115.0; the other central workers are exact.
- **Location:** `relaymesh/stats.py` → `worker_stats`
- **Why it fails:** Rounding the fraction and then multiplying by 100 brings binary float error back in, so 1.15 * 100 is 114.99999999999999. Scale first and round last.
- **Failing test:** `test_2_workers.TestWorkerStats.test_3_central_utilisation`
- **Unblocks:** test_3_central_utilisation.

Fix:

```diff
-            "utilisation_pct": round(busy_ms / WINDOW_MS, 3) * 100,
+            "utilisation_pct": round(100 * busy_ms / WINDOW_MS, 1),
```

Observed with only this bug applied (`tests.test_2_workers.TestWorkerStats.test_3_central_utilisation`):

```
AssertionError: {'cen-1': 114.99999999999999, 'cen-2': 52.0, 'cen-3': 33.0, 'cen-4': 0.0} != {'cen-1': 115.0, 'cen-2': 52.0, 'cen-3': 33.0, 'cen-4': 0.0}
- {'cen-1': 114.99999999999999, 'cen-2': 52.0, 'cen-3': 33.0, 'cen-4': 0.0}
?             ^ ^^^^^^^^^^^^^^

+ {'cen-1': 115.0, 'cen-2': 52.0, 'cen-3': 33.0, 'cen-4': 0.0}
?             ^ ^
```

### B4: Peak counter carried across workers

- **Type:** state-not-reset
- **Symptom:** Test 2 test_4_central_peak_inflight: every central worker reports peak 3 (cen-1 is right; cen-2 should be 2, cen-3 1, cen-4 0).
- **Location:** `relaymesh/stats.py` → `worker_stats`
- **Why it fails:** `peak` is set once before the loop, so each worker reports the running maximum of every worker before it in id order. cen-1's 3 leaks into cen-2, cen-3 and cen-4.
- **Failing test:** `test_2_workers.TestWorkerStats.test_4_central_peak_inflight`
- **Unblocks:** test_4_central_peak_inflight.

Fix:

```diff
     out = {}
-    peak = 0
     for wid in sorted(by_worker):
         reqs = by_worker[wid]
         busy_ms = sum(r.duration_ms for r in reqs)
         current = 0
+        peak = 0
```

Observed with only this bug applied (`tests.test_2_workers.TestWorkerStats.test_4_central_peak_inflight`):

```
AssertionError: {'cen-1': 3, 'cen-2': 3, 'cen-3': 3, 'cen-4': 3} != {'cen-1': 3, 'cen-2': 2, 'cen-3': 1, 'cen-4': 0}
- {'cen-1': 3, 'cen-2': 3, 'cen-3': 3, 'cen-4': 3}
?                       ^           ^           ^

+ {'cen-1': 3, 'cen-2': 2, 'cen-3': 1, 'cen-4': 0}
?                       ^           ^           ^
```

### B5: max_inflight 0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 3 test_5_rejected: only s01 is rejected; n02 and n06 are missing because north-2 served them.
- **Location:** `relaymesh/loader.py` → `load_workers`
- **Why it fails:** `or` treats an explicit 0 as missing, so the provisioning worker north-2 gets the default capacity of 2 and absorbs the north requests that should be rejected.
- **Failing test:** `test_3_summary.TestSummary.test_5_rejected`
- **Unblocks:** test_5_rejected.

Fix:

```diff
-            max_inflight=int(item.get("max_inflight") or DEFAULT_MAX_INFLIGHT),
+            max_inflight=int(item.get("max_inflight", DEFAULT_MAX_INFLIGHT)),
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_5_rejected`):

```
AssertionError: Lists differ: ['s01'] != ['n02', 'n06', 's01']

First differing element 0:
's01'
'n02'

Second list contains 2 additional elements.
First extra element 1:
'n06'

- ['s01']
+ ['n02', 'n06', 's01']
```

### B6: Out-of-rotation filter always true

- **Type:** or-precedence
- **Symptom:** Test 3 test_6_out_of_rotation: all 13 workers are listed instead of cen-4, east-3, west-2, west-3.
- **Location:** `relaymesh/report.py` → `out_of_rotation`
- **Why it fails:** The condition parses as `(w.state is DOWN) or WorkerState.DRAINING`, and an Enum member is truthy, so every worker passes the filter.
- **Failing test:** `test_3_summary.TestSummary.test_6_out_of_rotation`
- **Unblocks:** test_6_out_of_rotation.

Fix:

```diff
-        if w.state is WorkerState.DOWN or WorkerState.DRAINING
+        if w.state is WorkerState.DOWN or w.state is WorkerState.DRAINING
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_6_out_of_rotation`):

```
AssertionError: Lists differ: ['cen-1', 'cen-2', 'cen-3', 'cen-4', 'east-1', [77 chars]t-3'] != ['cen-4', 'east-3', 'west-2', 'west-3']

First differing element 0:
'cen-1'
'cen-4'

First list contains 9 additional elements.
First extra element 4:
'east-1'

+ ['cen-4', 'east-3', 'west-2', 'west-3']
- ['cen-1',
-  'cen-2',
-  'cen-3',
-  'cen-4',
-  'east-1',
-  'east-2',
-  'east-3',
-  'north-1',
 ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `relaymesh/health.py` → `apply_due`: The `<=` matches rule 1 (transitions at or before the arrival apply), and the cursor only moves forward because events are sorted by time in load_health.
- `relaymesh/stats.py` → `sweep_points`: Plain tuple sorting puts (t, -1) before (t, 1), so a request that ends exactly when another starts is counted as finished first, as the spec asks. It looks like it needs an explicit sort key, but it doesn't.
