# set-051 answer key: Lease book: heartbeats, expiry and dead-lettering

**Domain:** task_queue_leases  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_ledger.TestLedger.test_attempts`
- `tests.test_1_ledger.TestLedger.test_claims`
- `tests.test_1_ledger.TestLedger.test_rejected`
- `tests.test_1_ledger.TestLedger.test_status`
- `tests.test_2_report.TestReport.test_dead_letter`
- `tests.test_2_report.TestReport.test_extensions`
- `tests.test_2_report.TestReport.test_workers`

## Bugs (recommended order)

### B1: Event task ids only trimmed, not upper-cased

- **Type:** id-normalization
- **Symptom:** Tests 1 and 2: every heartbeat is rejected (the rejected list starts with alice's 09:05 heartbeat on 't01', and ids keep their lower case), and lower-case acks like dan's 't04' at 09:31 are rejected too. Status shows eight dead tasks (T01, T03, T04, T05, T07, T09 among them), `extensions` is {} and bob's 09:13 claim gets T01 instead of T02.
- **Location:** `leasebook/loader.py` → `load_events`
- **Why it fails:** Leases are keyed by the upper-cased ids from tasks.csv, but event ids are only trimmed. Every heartbeat and ack written as `t04`/` t02` fails the holder lookup and is rejected, so those leases expire instead of being extended or finished.
- **Unblocks:** Most of Test 1 (claims, status, rejected list) and the Test 2 worker table. It also exposes B3.

Fix:

```diff
-                task_id=clean(row["task"]),
+                task_id=norm_task(row["task"]),
```

Observed with only this bug applied (`tests.test_1_ledger.TestLedger.test_attempts`):

```
AssertionError: {'T01[52 chars] 2, 'T07': 2, 'T08': 0, 'T09': 2, 'T10': 1, 'T11': 1, 'T12': 0} != {'T01[52 chars] 2, 'T07': 1, 'T08': 0, 'T09': 2, 'T10': 1, 'T11': 1, 'T12': 1}
  {'T01': 2,
   'T02': 3,
   'T03': 2,
   'T04': 2,
   'T05': 1,
   'T06': 2,
-  'T07': 2,
?         ^

+  'T07': 1,
?         ^

   'T08': 0,
   'T09': 2,
   'T10': 1,
   'T11': 1,
-  'T12': 0}
?         ^

+  'T12': 1}
?  ...
```

### B2: Reap removes leases from the list it is looping over

- **Type:** mutate-while-iterating
- **Symptom:** Tests 1 and 2: cara's 09:12 ack of T04 is accepted (it is missing from the rejected list), so dan's 09:22 claim gets T05 instead of T04. T05 and T11 end up dead, T04 shows 1 attempt, `extensions` loses T05 and dan shows 0 acks / 2 lost.
- **Location:** `leasebook/ledger.py` → `Ledger.reap`
- **Why it fails:** Removing an item from a list while iterating it shifts the next item into the slot the loop has already visited, so the lease right after each expired one is skipped. At 09:12 bob's T02 expires and cara's T04, which also expired, survives, so her ack is accepted.
- **Unblocks:** Test 1 claims/status/rejected and the Test 2 worker table.

Fix:

```diff
-        for lease in self.active:
+        for lease in list(self.active):
```

Observed with only this bug applied (`tests.test_1_ledger.TestLedger.test_attempts`):

```
AssertionError: {'T01[28 chars]04': 1, 'T05': 1, 'T06': 2, 'T07': 1, 'T08': 0[36 chars]': 1} != {'T01[28 chars]04': 2, 'T05': 1, 'T06': 2, 'T07': 1, 'T08': 0[36 chars]': 1}
  {'T01': 2,
   'T02': 3,
   'T03': 2,
-  'T04': 1,
?         ^

+  'T04': 2,
?         ^

   'T05': 1,
   'T06': 2,
   'T07': 1,
   'T08': 0,
   'T09': 2,
   'T10': 1,
-  'T11': 2,
?         ^

+  'T11': 1,
?         ^

   'T1 ...
```

### B3: Third heartbeat accepted

- **Type:** off-by-one
- **Symptom:** Only visible after B1 is fixed. Tests 1 and 2: alice's third heartbeat at 09:20 is accepted, `extensions` shows T01: 3, and her 09:25 ack goes through. erin's 09:26 claim then gets T02 instead of T01, T03 and T10 end up dead, and alice shows 1 ack / 1 lost.
- **Location:** `leasebook/ledger.py` → `Ledger.heartbeat`
- **Why it fails:** The README allows a heartbeat only while the lease has been extended fewer than 2 times. `>` lets a third extension through, so alice's T01 lease runs to 09:30 and her 09:25 ack is accepted.
- **Unblocks:** Test 1 and Test 2 fully pass.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-        if lease is None or lease.extensions > MAX_EXTENSIONS:
+        if lease is None or lease.extensions >= MAX_EXTENSIONS:
```

Observed with only this bug applied (`tests.test_1_ledger.TestLedger.test_attempts`):

```
AssertionError: {'T01': 1, 'T02': 3, 'T03': 2, 'T04': 2, 'T05': 1[66 chars]': 1} != {'T01': 2, 'T02': 3, 'T03': 2, 'T04': 2, 'T05': 1[66 chars]': 1}
- {'T01': 1,
?         ^

+ {'T01': 2,
?         ^

   'T02': 3,
   'T03': 2,
   'T04': 2,
   'T05': 1,
   'T06': 2,
   'T07': 1,
   'T08': 0,
   'T09': 2,
-  'T10': 2,
?         ^

+  'T10': 1,
?         ^

   'T11': 1,
   'T12': 1}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `leasebook/ledger.py` → `next_pending`: It uses min() on (priority, created_at, id). That looks backwards to anyone who reads 'priority' as 'bigger wins', but the README says 1 is the most urgent, so the smallest number has to come first.
