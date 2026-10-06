# set-099 answer key: Lease broker replay with heartbeats and nacks

**Domain:** task_queue_leases  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_replay.TestReplay.test_expired_leases` | B1 Leases removed while iterating |
| `test_1_replay.TestReplay.test_rejected_events` | B2 Generic lease error matched before TaskClosed |
| `test_2_report.TestReport.test_mean_ack_seconds` | B3 Mean ack time floor-divided |

## Failing pattern with all bugs present

- `tests.test_1_replay.TestReplay.test_expired_leases`
- `tests.test_1_replay.TestReplay.test_rejected_events`
- `tests.test_2_report.TestReport.test_mean_ack_seconds`

## Bugs (recommended order)

### B1: Leases removed while iterating

- **Type:** mutate-while-iterating
- **Symptom:** Test 1 test_expired_leases: K05's expiry is logged at 08:02:40 instead of 08:02:30. Dispatch, statuses and attempts are all unchanged.
- **Location:** `leasehold/broker.py` → `Broker.reap`
- **Why it fails:** reap removes items from self.leases while looping over it. When K12's lease is removed, K05's lease (next in the list, also expired) slides into its slot and the loop steps past it. K05 is only reaped at the next event.
- **Failing test:** `test_1_replay.TestReplay.test_expired_leases`
- **Unblocks:** test_1_replay.TestReplay.test_expired_leases

Fix:

```diff
-        for lease in self.leases:
+        for lease in list(self.leases):
```

Observed with only this bug applied (`tests.test_1_replay.TestReplay.test_expired_leases`):

```
AssertionError: Lists differ: [['08[27 chars]8:02:40', 'w02', 'K05'], ['08:05:40', 'w02', '[113 chars]04']] != [['08[27 chars]8:02:30', 'w02', 'K05'], ['08:05:40', 'w02', '[113 chars]04']]

First differing element 1:
['08:02:40', 'w02', 'K05']
['08:02:30', 'w02', 'K05']

  [['08:02:30', 'w05', 'K12'],
-  ['08:02:40', 'w02', 'K05'],
?          ^

+  ['08:02:30', 'w02', 'K05'],
?          ^

   ['08 ...
```

### B2: Generic lease error matched before TaskClosed

- **Type:** exception-order
- **Symptom:** Test 1 test_rejected_events: the 08:04:00 ack of K02 and the 08:09:40 ack of K07 are logged as 'not_holder' instead of 'closed'.
- **Location:** `leasehold/broker.py` → `Broker.handle`
- **Why it fails:** handle() takes the first REJECTION_REASONS entry the exception is an instance of. TaskClosed is a subclass of LeaseError, so with LeaseError listed first every TaskClosed is reported as not_holder. The more specific class has to come first, as with except clauses.
- **Failing test:** `test_1_replay.TestReplay.test_rejected_events`
- **Unblocks:** test_1_replay.TestReplay.test_rejected_events

Fix:

```diff
+    (TaskClosed, "closed"),
     (LeaseError, "not_holder"),
-    (TaskClosed, "closed"),
```

Observed with only this bug applied (`tests.test_1_replay.TestReplay.test_rejected_events`):

```
AssertionError: Lists differ: [['08[129 chars]2', 'not_holder'], ['08:06:20', 'w02', 'nack',[226 chars]er']] != [['08[129 chars]2', 'closed'], ['08:06:20', 'w02', 'nack', 'K0[218 chars]er']]

First differing element 2:
['08:04:00', 'w01', 'ack', 'K02', 'not_holder']
['08:04:00', 'w01', 'ack', 'K02', 'closed']

Diff is 721 characters long. Set self.maxDiff to None to see it.
```

### B3: Mean ack time floor-divided

- **Type:** integer-division
- **Symptom:** Test 2 test_mean_ack_seconds: audio 336 and ocr 136 instead of 336.7 and 136.7. Review (160.0) is unaffected.
- **Location:** `leasehold/reports.py` → `ack_times`
- **Why it fails:** `//` floor-divides the summed seconds before rounding, so the fractional part is gone and round(..., 1) has nothing left to round.
- **Failing test:** `test_2_report.TestReport.test_mean_ack_seconds`
- **Unblocks:** test_2_report.TestReport.test_mean_ack_seconds

Fix:

```diff
-    return {t: round(sum(s) // len(s), 1) for t, s in sorted(spans.items())}
+    return {t: round(sum(s) / len(s), 1) for t, s in sorted(spans.items())}
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_mean_ack_seconds`):

```
AssertionError: {'audio': 336, 'ocr': 136, 'review': 160} != {'audio': 336.7, 'ocr': 136.7, 'review': 160.0}
- {'audio': 336, 'ocr': 136, 'review': 160}
+ {'audio': 336.7, 'ocr': 136.7, 'review': 160.0}
?              ++            ++               ++
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `leasehold/broker.py` → `is_expired`: `>=` looks like an off-by-one, but rule 1 says a lease is expired when now >= expires_at, so a lease ending exactly at an event's time is reaped before that event.
- `leasehold/broker.py` → `pick_next`: min() over (priority, created_at, id) looks like it might pick the least urgent task, but priority 1 is the most urgent here, so the smallest number first is right. Earliest creation and lowest id are the tie-breaks from rule 3.
