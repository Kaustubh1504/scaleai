# set-075 answer key: Lease broker replay with checkpoint snapshot

**Domain:** task_queue_leases  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_replay.TestReplay.test_checkpoint` | B1 Checkpoint snapshot is a shallow copy |
| `test_2_summary.TestSummary.test_rejections` | B2 Base exception matched first |
| `test_2_summary.TestSummary.test_wait_stats` | B3 max wait reported in milliseconds |

## Failing pattern with all bugs present

- `tests.test_1_replay.TestReplay.test_checkpoint`
- `tests.test_2_summary.TestSummary.test_rejections`
- `tests.test_2_summary.TestSummary.test_wait_stats`

## Bugs (recommended order)

### B1: Checkpoint snapshot is a shallow copy

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 1 test_checkpoint: the checkpoint view equals the final view: T02 shows dead instead of leased by W4, T08/T09 done instead of ready, T10 done instead of leased by W2, T11 leased by W1 instead of ready.
- **Location:** `leasebox/replay.py` → `snapshot`
- **Why it fails:** dict(tasks) copies the mapping but keeps the same Task objects, which the broker keeps mutating after the checkpoint. The snapshot ends up showing the final state.
- **Failing test:** `test_1_replay.TestReplay.test_checkpoint`
- **Unblocks:** test_checkpoint.

Fix:

```diff
-    return dict(tasks)
+    return copy.deepcopy(tasks)
```

Observed with only this bug applied (`tests.test_1_replay.TestReplay.test_checkpoint`):

```
AssertionError: {'T01[65 chars]e': 'dead', 'owner': None, 'attempts': 3}, 'T0[554 chars]: 0}} != {'T01[65 chars]e': 'leased', 'owner': 'W4', 'attempts': 3}, '[559 chars]: 0}}
  {'T01': {'attempts': 1, 'owner': None, 'state': 'done'},
-  'T02': {'attempts': 3, 'owner': None, 'state': 'dead'},
?                                  ^^^^            ^

+  'T02': {'attempts': 3, 'owner': 'W4', 'state': 'le ...
```

### B2: Base exception matched first

- **Type:** exception-order
- **Symptom:** Test 2 test_rejections: {'expired': 0, 'not_owner': 0, 'invalid': 7} instead of {'expired': 4, 'not_owner': 2, 'invalid': 1}.
- **Location:** `leasebox/broker.py` → `rejection_code`
- **Why it fails:** rejection_code returns the first class that isinstance() matches. LeaseExpired and NotOwner both subclass LeaseError, so with the base class first every rejection becomes 'invalid'.
- **Failing test:** `test_2_summary.TestSummary.test_rejections`
- **Unblocks:** test_rejections.

Fix:

```diff
-REJECTION_CODES = [(LeaseError, "invalid"), (LeaseExpired, "expired"), (NotOwner, "not_owner")]
+REJECTION_CODES = [(LeaseExpired, "expired"), (NotOwner, "not_owner"), (LeaseError, "invalid")]
```

Observed with only this bug applied (`tests.test_2_summary.TestSummary.test_rejections`):

```
AssertionError: {'expired': 0, 'not_owner': 0, 'invalid': 7} != {'expired': 4, 'not_owner': 2, 'invalid': 1}
- {'expired': 0, 'invalid': 7, 'not_owner': 0}
?             ^             ^               ^

+ {'expired': 4, 'invalid': 1, 'not_owner': 2}
?             ^             ^               ^
```

### B3: max wait reported in milliseconds

- **Type:** ms-vs-s
- **Symptom:** Test 2 test_wait_stats: max_s is 230000 instead of 230.0; mean_s is correct at 48.8.
- **Location:** `leasebox/reports.py` → `wait_stats`
- **Why it fails:** Waits are differences of epoch milliseconds. mean_s divides by 1000 but max_s does not, so it reports 230000 instead of 230.0.
- **Failing test:** `test_2_summary.TestSummary.test_wait_stats`
- **Unblocks:** test_wait_stats.

Fix:

```diff
-        "max_s": round(max(waits), 1),
+        "max_s": round(max(waits) / 1000, 1),
```

Observed with only this bug applied (`tests.test_2_summary.TestSummary.test_wait_stats`):

```
AssertionError: {'mean_s': 48.8, 'max_s': 230000} != {'mean_s': 48.8, 'max_s': 230.0}
- {'max_s': 230000, 'mean_s': 48.8}
?              ^^

+ {'max_s': 230.0, 'mean_s': 48.8}
?              ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `leasebox/broker.py` → `lease_expired`: `>=` looks like it expires leases one tick early, but rule 2 says a lease expiring at or before the event time has expired. W3's heartbeat at exactly 70 s on a lease expiring at 70 s must be rejected.
- `leasebox/broker.py` → `next_task`: min() over (priority, enqueued_ms, id) looks like it might pick the least important task, but priority 1 is the most urgent, so the smallest tuple is the right one. It also filters out tasks enqueued after now (T06 before 60 s).
