# set-043 answer key: Workshop seat holds with 10-minute expiry

**Domain:** seat_reservation  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_ledger.TestLedgerOutcomes.test_hold_expiry` | B1 Hold age read with timedelta.seconds |
| `test_1_ledger.TestLedgerOutcomes.test_rejection_reasons` | B2 Event session ids upper-cased but not trimmed |
| `test_2_report.TestReport.test_attendee_seats` | B3 Cancelled bookings counted in attendee seats |

## Failing pattern with all bugs present

- `tests.test_1_ledger.TestLedgerOutcomes.test_hold_expiry`
- `tests.test_1_ledger.TestLedgerOutcomes.test_rejection_reasons`
- `tests.test_2_report.TestReport.test_attendee_seats`

## Bugs (recommended order)

### B1: Hold age read with timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** test_1 test_hold_expiry: E35 is 'ok' instead of 'expired' and E36 is 'ok' instead of 'nothing_to_cancel'. E05's 12-minute expiry is still right, and the report is unchanged.
- **Location:** `seatbook/engine.py` → `is_expired`
- **Why it fails:** `timedelta.seconds` is only the seconds part after whole days are taken out. zed's hold is 1 day 6 minutes old, so `.seconds` is 360 and the hold looks fresh. The late confirm succeeds, and the later cancel then finds a booking to cancel.
- **Failing test:** `test_1_ledger.TestLedgerOutcomes.test_hold_expiry`
- **Unblocks:** test_hold_expiry

Fix:

```diff
-    return (now - hold.held_at).seconds > HOLD_SECONDS
+    return (now - hold.held_at).total_seconds() > HOLD_SECONDS
```

Observed with only this bug applied (`tests.test_1_ledger.TestLedgerOutcomes.test_hold_expiry`):

```
AssertionError: {'E04[35 chars]ok', 'E07': 'ok', 'E35': 'ok', 'E36': 'ok'} != {'E04[35 chars]ok', 'E07': 'ok', 'E35': 'expired', 'E36': 'nothing_to_cancel'}
  {'E04': 'ok',
   'E05': 'expired',
   'E06': 'ok',
   'E07': 'ok',
-  'E35': 'ok',
-  'E36': 'ok'}
+  'E35': 'expired',
+  'E36': 'nothing_to_cancel'}
```

### B2: Event session ids upper-cased but not trimmed

- **Type:** id-normalization
- **Symptom:** test_1 test_rejection_reasons: E17 is 'unknown_session' instead of 'full'. Everything else matches.
- **Location:** `seatbook/loader.py` → `load_events`
- **Why it fails:** The session ids in events.csv are only upper-cased, so E17's ' WS-09' keeps its leading space and doesn't match the trimmed key from sessions.csv. It is reported as unknown_session instead of full. The mixed-case ids still match, which hides the problem.
- **Failing test:** `test_1_ledger.TestLedgerOutcomes.test_rejection_reasons`
- **Unblocks:** test_rejection_reasons

Fix:

```diff
-                session_id=row["session_id"].upper(),
+                session_id=norm_session(row["session_id"]),
```

Observed with only this bug applied (`tests.test_1_ledger.TestLedgerOutcomes.test_rejection_reasons`):

```
AssertionError: {'E03[44 chars]7': 'unknown_session', 'E18': 'unknown_session[67 chars]ull'} != {'E03[44 chars]7': 'full', 'E18': 'unknown_session', 'E20': '[56 chars]ull'}
  {'E03': 'full',
   'E09': 'full',
   'E15': 'full',
-  'E17': 'unknown_session',
+  'E17': 'full',
   'E18': 'unknown_session',
   'E20': 'duplicate',
   'E22': 'no_hold',
   'E24': 'closed',
   'E34': 'full'}
```

### B3: Cancelled bookings counted in attendee seats

- **Type:** or-precedence
- **Symptom:** test_2 test_attendee_seats: an extra 'dev@lab.io': 3 entry (dev cancelled that booking). Session occupancy is unaffected.
- **Location:** `seatbook/report.py` → `attendee_seats`
- **Why it fails:** `b.status == "confirmed" or "comped"` parses as `(b.status == "confirmed") or "comped"`, and the non-empty string is always truthy, so every booking counts, including dev's cancelled 3 seats.
- **Failing test:** `test_2_report.TestReport.test_attendee_seats`
- **Unblocks:** test_attendee_seats

Fix:

```diff
-        if b.status == "confirmed" or "comped":
+        if b.status == "confirmed" or b.status == "comped":
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_attendee_seats`):

```
AssertionError: {'ana[44 chars] 1, 'dev@lab.io': 3, 'eli@lab.io': 1, 'fay@lab[54 chars]': 3} != {'ana[44 chars] 1, 'eli@lab.io': 1, 'fay@lab.io': 2, 'hana@la[37 chars]': 3}
  {'ana@lab.io': 5,
   'ben@lab.io': 2,
   'cara@lab.io': 1,
-  'dev@lab.io': 3,
   'eli@lab.io': 1,
   'fay@lab.io': 2,
   'hana@lab.io': 2,
   'kim@lab.io': 3,
   'mo@lab.io': 3}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `seatbook/engine.py` → `has_room`: `left - seats >= 0` is the same as seats <= left, which is rule 2 (in use + requested at most capacity). E02 fills WS-01 exactly and is accepted, as it should be.
