# set-027 answer key: Lease heartbeats with epoch-ms replay

**Domain:** task_queue_leases  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_replay.TestReplay.test_heartbeats` | B1 Heartbeat at the deadline accepted |
| `test_2_report.TestReport.test_completed_by` | B2 Completion list shared by every worker |
| `test_2_report.TestReport.test_mean_wait` | B3 Mean wait reported in milliseconds |

## Failing pattern with all bugs present

- `tests.test_1_replay.TestReplay.test_heartbeats`
- `tests.test_2_report.TestReport.test_completed_by`
- `tests.test_2_report.TestReport.test_mean_wait`

## Bugs (recommended order)

### B1: Heartbeat at the deadline accepted

- **Type:** time-window-boundary
- **Symptom:** 
- **Location:** `leasebeat/broker.py` → `Broker.reap`
- **Why it fails:** Rule 1 expires a lease when now ≥ deadline. With `>`, w2's heartbeat at exactly 08:01:50 (T02's deadline) finds the lease still live and extends it. No lease event comes before the extended deadline, so the dispatch log doesn't change.
- **Failing test:** `test_1_replay.TestReplay.test_heartbeats`
- **Unblocks:** test_1_replay test_heartbeats.

Fix:

```diff
-            if now_ms > lease.deadline_ms:
+            if now_ms >= lease.deadline_ms:
```

Observed with only this bug applied (`tests.test_1_replay.TestReplay.test_heartbeats`):

```
AssertionError: Lists differ: [['08[84 chars]2', 'ok'], ['08:02:10', 'w3', 'T10', 'ok'], ['[25 chars]ok']] != [['08[84 chars]2', 'rejected'], ['08:02:10', 'w3', 'T10', 'ok[31 chars]ok']]

First differing element 2:
['08:01:50', 'w2', 'T02', 'ok']
['08:01:50', 'w2', 'T02', 'rejected']

  [['08:00:50', 'w2', 'T02', 'ok'],
   ['08:01:20', 'w1', 'T05', 'ok'],
-  ['08:01:50', 'w2', 'T02', 'ok'],
?      ...
```

### B2: Completion list shared by every worker

- **Type:** shared-class-attribute
- **Symptom:** 
- **Location:** `leasebeat/models.py` → `Worker`
- **Why it fails:** `completed` is a class attribute, so `self.completed.append` mutates one list shared by every Worker instance (and by every replay in the same process). Each worker reports everyone's completions.
- **Failing test:** `test_2_report.TestReport.test_completed_by`
- **Unblocks:** test_2_report test_completed_by.

Fix:

```diff
     """A worker seen in the event log, with the tasks it finished in order."""
 
-    completed = []
-
     def __init__(self, worker_id):
         self.worker_id = worker_id
+        self.completed = []
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_completed_by`):

```
AssertionError: {'w1': ['T08', 'T04', 'T05', 'T10', 'T02', 'T01', 'T03', 'T[536 chars]09']} != {'w1': ['T08', 'T05', 'T02'], 'w2': ['T01'], 'w3': ['T04', [32 chars]09']}
Diff is 1581 characters long. Set self.maxDiff to None to see it.
```

### B3: Mean wait reported in milliseconds

- **Type:** ms-vs-s
- **Symptom:** 
- **Location:** `leasebeat/reports.py` → `mean_wait_seconds`
- **Why it fails:** All times are kept as epoch milliseconds, so the waits are in ms. Without dividing by 1000, the mean comes out 1000× too large.
- **Failing test:** `test_2_report.TestReport.test_mean_wait`
- **Unblocks:** test_2_report test_mean_wait.

Fix:

```diff
-    return round(statistics.mean(waits), 1) if waits else None
+    return round(statistics.mean(waits) / 1000, 1) if waits else None
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_mean_wait`):

```
AssertionError: 821500 != 821.5
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `leasebeat/broker.py` → `pick_next`: min() on (priority, enqueued_ms, task_id) looks like it might be backwards for priority, but this README says 1 is the most urgent, so the smallest number should win. The tie-breaks match rule 3.
- `leasebeat/loader.py` → `to_ms`: Treating an all-digit string as epoch milliseconds matches the README, and the parsed formats are pinned to UTC before converting, multiplying seconds by 1000.
