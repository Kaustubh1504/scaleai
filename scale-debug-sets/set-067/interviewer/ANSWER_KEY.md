# set-067 answer key: Box-office holds: seat order, overnight expiry, action routing

**Domain:** seat_reservation  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_holds.TestHolds.test_orchestra_holds` | B1 Seat numbers kept as strings |
| `test_1_holds.TestHolds.test_balcony_holds` | B2 Hold age read from timedelta.seconds |
| `test_2_report.TestReport.test_ignored_requests` | B3 Release branch condition always true |

## Failing pattern with all bugs present

- `tests.test_1_holds.TestHolds.test_balcony_holds`
- `tests.test_1_holds.TestHolds.test_orchestra_holds`
- `tests.test_2_report.TestReport.test_ignored_requests`

## Bugs (recommended order)

### B1: Seat numbers kept as strings

- **Type:** string-vs-int
- **Symptom:** Test 1 test_orchestra_holds: R01 gets ORCH-A1, A10, A11, A12 instead of A1-A4, and R02, R04 and R07 shift the same way (e.g. R04 gets A6, A7, A8). Row B and the balcony are unchanged.
- **Location:** `seatbook/loader.py` → `load_seats`
- **Why it fails:** With string numbers, best_available's sort is lexicographic, so '10', '11', '12' come before '2'. Only orchestra row A has seats numbered 10+, so only those holds change.
- **Failing test:** `test_1_holds.TestHolds.test_orchestra_holds`
- **Unblocks:** test_orchestra_holds.

Fix:

```diff
-                number=clean(row["number"]),
+                number=int(row["number"]),
```

Observed with only this bug applied (`tests.test_1_holds.TestHolds.test_orchestra_holds`):

```
AssertionError: {'R01[17 chars]RCH-A10', 'ORCH-A11', 'ORCH-A12'], 'R02': ['OR[184 chars]B3']} != {'R01[17 chars]RCH-A2', 'ORCH-A3', 'ORCH-A4'], 'R02': ['ORCH-[184 chars]B3']}
- {'R01': ['ORCH-A1', 'ORCH-A10', 'ORCH-A11', 'ORCH-A12'],
?                            ^^          ^^          ^^

+ {'R01': ['ORCH-A1', 'ORCH-A2', 'ORCH-A3', 'ORCH-A4'],
?                            ^          ^          ^
 ...
```

### B2: Hold age read from timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 1 test_balcony_holds: R17 (erin, May 2 18:05) gets BALC-A3/A4 instead of A1/A2, and R22 gets A1/A2 instead of A3/A4. Dora's May 1 18:00 hold was still blocking A1/A2.
- **Location:** `seatbook/booking.py` → `Venue.expire`
- **Why it fails:** timedelta.seconds is only the seconds part after whole days. Dora's hold from 18:00 on May 1 is 1 day 5 minutes old at 18:05 on May 2, but .seconds says 300, so the hold survives and blocks BALC-A1/A2.
- **Failing test:** `test_1_holds.TestHolds.test_balcony_holds`
- **Unblocks:** test_balcony_holds.

Fix:

```diff
-            age = (now - hold.held_at).seconds
+            age = (now - hold.held_at).total_seconds()
```

Observed with only this bug applied (`tests.test_1_holds.TestHolds.test_balcony_holds`):

```
AssertionError: {'R09[67 chars], 'R17': ['BALC-A3', 'BALC-A4'], 'R22': ['BALC-A1', 'BALC-A2']} != {'R09[67 chars], 'R17': ['BALC-A1', 'BALC-A2'], 'R22': ['BALC-A3', 'BALC-A4']}
  {'R09': ['BALC-A1', 'BALC-A2', 'BALC-A3'],
   'R16': ['BALC-A1', 'BALC-A2'],
-  'R17': ['BALC-A3', 'BALC-A4'],
?                 ^          ^

+  'R17': ['BALC-A1', 'BALC-A2'],
?                 ^          ^

-  'R22': [' ...
```

### B3: Release branch condition always true

- **Type:** or-precedence
- **Symptom:** Test 2 test_ignored_requests: the ignored list is [] instead of ['R08', 'R20']. The upgrade and refund requests were handled as releases (outcome noop).
- **Location:** `seatbook/booking.py` → `Venue.handle`
- **Why it fails:** `a == 'release' or 'cancel'` is `(a == 'release') or 'cancel'`, and the non-empty string is truthy, so every action that isn't hold or confirm goes through release. 'upgrade' and 'refund' come out as noop instead of ignored.
- **Failing test:** `test_2_report.TestReport.test_ignored_requests`
- **Unblocks:** test_ignored_requests.

Fix:

```diff
-        elif req.action == "release" or "cancel":
+        elif req.action == "release" or req.action == "cancel":
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_ignored_requests`):

```
AssertionError: Lists differ: [] != ['R08', 'R20']

Second list contains 2 additional elements.
First extra element 0:
'R08'

- []
+ ['R08', 'R20']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `seatbook/booking.py` → `best_available`: It filters to available seats in the section, sorts by (row, number) and refuses partial holds with `len(free) < quantity`. The slice [:quantity] is exact. It is only as good as the types it is given: if number were a string, the sort would be lexicographic, but that would be a loader problem, not this function's.
