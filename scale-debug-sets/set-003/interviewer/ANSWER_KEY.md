# set-003 answer key: Task lease replay with expiry and dead-lettering

**Domain:** task_queue_leases  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_dispatch.TestDispatch.test_dispatch_log`
- `tests.test_1_dispatch.TestDispatch.test_first_lease_gets_most_urgent_task`
- `tests.test_2_final_state.TestFinalState.test_attempts`
- `tests.test_2_final_state.TestFinalState.test_completed_by`
- `tests.test_2_final_state.TestFinalState.test_dead_letter`
- `tests.test_2_final_state.TestFinalState.test_rejected_completions`
- `tests.test_2_final_state.TestFinalState.test_status`

## Bugs (recommended order)

### B1: Priority loaded as a string

- **Type:** string-vs-int
- **Symptom:** Test 1: the first lease hands out A-106 (priority 9) instead of A-101 (priority 12). A-101 and A-103 are never leased at all. Test 2: tasks the workers did finish get marked dead or pending, and completed_by collapses to {'w1': 1}.
- **Location:** `leasequeue/loader.py` → `load_tasks`
- **Why it fails:** Priorities stay strings, so the descending sort is lexicographic: '9' > '7' > '12' > '10'. Nothing crashes, because pick_next only ever compares priorities with each other.
- **Unblocks:** Test 1, and most of Test 2.

Fix:

```diff
-                priority=clean(row["priority"]),
+                priority=int(clean(row["priority"])),
```

Observed with only this bug applied (`tests.test_1_dispatch.TestDispatch.test_dispatch_log`):

```
AssertionError: Lists differ: [['20[23 chars]'A-106'], ['2026-04-01 08:01', 'w2', 'A-102'],[291 chars]09']] != [['20[23 chars]'A-101'], ['2026-04-01 08:01', 'w2', 'A-103'],[291 chars]09']]

First differing element 0:
['2026-04-01 08:00', 'w1', 'A-106']
['2026-04-01 08:00', 'w1', 'A-101']

- [['2026-04-01 08:00', 'w1', 'A-106'],
?                                  ^

+ [['2026-04-01 08:00', 'w1', 'A ...
```

### B2: Lease age measured with timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 2 only: A-110 ends up 'done' (w4 'completes' it at 08:46 on day 2) instead of 'dead', completed_by gains w4, and the 08:46 w4 row is missing from rejected. The day-1 lease was still treated as live the next morning.
- **Location:** `leasequeue/broker.py` → `Broker.reap`
- **Why it fails:** timedelta.seconds is only the seconds part (0-86399) and drops whole days. A lease that is 1 day and 5 minutes old reads as 300 seconds, so it looks live.
- **Unblocks:** Test 2 for A-110. This exposes B3.

Fix:

```diff
-            if (now - lease.leased_at).seconds >= LEASE_SECONDS:
+            if (now - lease.leased_at).total_seconds() >= LEASE_SECONDS:
```

Observed with only this bug applied (`tests.test_2_final_state.TestFinalState.test_completed_by`):

```
AssertionError: {'w1': 3, 'w2': 2, 'w4': 1, 'w5': 1} != {'w1': 3, 'w2': 2, 'w5': 1}
- {'w1': 3, 'w2': 2, 'w4': 1, 'w5': 1}
?                   ---------

+ {'w1': 3, 'w2': 2, 'w5': 1}
```

### B3: Dead-letter check allows one extra attempt

- **Type:** retry-off-by-one
- **Symptom:** Only visible after B2 is fixed. On day 2, w2 leases A-110 a third time (attempts 3, max 2) instead of getting A-104, so A-104 ends up pending and w2's 08:59 completion is rejected.
- **Location:** `leasequeue/models.py` → `Task.exhausted`
- **Why it fails:** attempts counts leases already taken. Once attempts equals max_attempts there are none left, so the check has to be >=. With > the task gets max_attempts + 1 leases.
- **Unblocks:** Tests 1 and 2 fully.
- **Masked:** invisible until B2 is fixed (identical test output either way).

Fix:

```diff
-        return self.attempts > self.max_attempts
+        return self.attempts >= self.max_attempts
```

Observed with only this bug applied (`tests.test_1_dispatch.TestDispatch.test_dispatch_log`):

```
AssertionError: Lists differ: [['20[244 chars] 'A-110'], ['2026-04-02 08:50', 'w3', 'A-104'][70 chars]08']] != [['20[244 chars] 'A-104'], ['2026-04-02 08:50', 'w3', 'A-108'][70 chars]09']]

First differing element 6:
['2026-04-02 08:45', 'w2', 'A-110']
['2026-04-02 08:45', 'w2', 'A-104']

  [['2026-04-01 08:00', 'w1', 'A-101'],
   ['2026-04-01 08:01', 'w2', 'A-103'],
   ['2026-04-01 08:06', 'w3',  ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `leasequeue/broker.py` → `pick_next`: It is a two-pass stable sort. The first pass orders by (created_at, id) and the second by priority, descending. Python's sort is stable, so ties on priority keep the created_at/id order. It looks backwards, but it is correct, as long as priority is really an int.
