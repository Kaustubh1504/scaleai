# set-019 answer key: Box office seat holds with a 10-minute window

**Domain:** seat_reservation  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_bookings.TestBookings.test_by_customer`
- `tests.test_1_bookings.TestBookings.test_sold_seats`
- `tests.test_2_report.TestReport.test_occupancy`
- `tests.test_2_report.TestReport.test_rejections`
- `tests.test_2_report.TestReport.test_revenue`

## Bugs (recommended order)

### B1: Customer ids only trimmed, not upper-cased

- **Type:** id-normalization
- **Symptom:** Test 1: B1, B3 and A6 are missing from sold, and C03/C05 are missing from by_customer (C02 only has A2). Test 2: no_hold is 6 instead of 3, revenue 436.0 instead of 627.0, occupancy 35.0 instead of 50.0.
- **Location:** `boxoffice/loader.py` → `load_events`
- **Why it fails:** Holds written as `c03`/` c05`/`c02` and confirms written as `C03`/`C05`/`C02` no longer belong to the same customer, so each of those confirms fails the holder check and is rejected as no_hold.
- **Unblocks:** B1, B3 and A6 in the sold map, C02/C03/C05 in by_customer, and the Test 2 numbers. Exposes B2.

Fix:

```diff
-                customer=clean(row["customer"]),
+                customer=norm_id(row["customer"]),
```

Observed with only this bug applied (`tests.test_1_bookings.TestBookings.test_by_customer`):

```
AssertionError: {'C01[18 chars]['A2'], 'C06': ['B2'], 'C08': ['C1'], 'C11': [[22 chars]A4']} != {'C01[18 chars]['A2', 'A6'], 'C03': ['B1'], 'C05': ['B3'], 'C[58 chars]A4']}
  {'C01': ['A1'],
-  'C02': ['A2'],
+  'C02': ['A2', 'A6'],
?              ++++++

+  'C03': ['B1'],
+  'C05': ['B3'],
   'C06': ['B2'],
   'C08': ['C1'],
   'C11': ['C2'],
   'C12': ['A3', 'A4']}
```

### B2: Hold window made exclusive

- **Type:** time-window-boundary
- **Symptom:** Only visible after B1 is fixed. Test 1: B3 is not sold and C05 is missing from by_customer. Test 2: no_hold 4, revenue 571.5, occupancy 45.0.
- **Location:** `boxoffice/booking.py` → `is_active`
- **Why it fails:** C05's confirm (E10) comes exactly 10:00 after the hold (E09). The spec says that is still in time, but `<` treats the hold as already expired.
- **Unblocks:** B3 in the sold map, C05 in by_customer, and the Test 2 numbers.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-    return hold is not None and age_seconds(hold.held_at, now) < HOLD_SECONDS
+    return hold is not None and age_seconds(hold.held_at, now) <= HOLD_SECONDS
```

Observed with only this bug applied (`tests.test_1_bookings.TestBookings.test_by_customer`):

```
AssertionError: {'C01[45 chars], 'C06': ['B2'], 'C08': ['C1'], 'C11': ['C2'],[16 chars]A4']} != {'C01[45 chars], 'C05': ['B3'], 'C06': ['B2'], 'C08': ['C1'],[31 chars]A4']}
  {'C01': ['A1'],
   'C02': ['A2', 'A6'],
   'C03': ['B1'],
+  'C05': ['B3'],
   'C06': ['B2'],
   'C08': ['C1'],
   'C11': ['C2'],
   'C12': ['A3', 'A4']}
```

### B3: Hold age ignores whole days

- **Type:** timedelta-seconds
- **Symptom:** Test 1: C2 is sold to C10 instead of C11. Test 2: seat_held is 2 instead of 1 (no_hold stays 3: C11's confirm is rejected and C10's goes through). Revenue and occupancy are unchanged.
- **Location:** `boxoffice/utils.py` → `age_seconds`
- **Why it fails:** `timedelta.seconds` is only the seconds part after whole days are removed. C10's hold from day 1 looks 2 minutes old on day 2, so it blocks C11's hold and then lets C10 confirm.
- **Unblocks:** C2 in the sold map and by_customer, and the seat_held/no_hold counts.

Fix:

```diff
-    return (later - earlier).seconds
+    return (later - earlier).total_seconds()
```

Observed with only this bug applied (`tests.test_1_bookings.TestBookings.test_by_customer`):

```
AssertionError: {'C01[64 chars]06': ['B2'], 'C08': ['C1'], 'C10': ['C2'], 'C12': ['A3', 'A4']} != {'C01[64 chars]06': ['B2'], 'C08': ['C1'], 'C11': ['C2'], 'C12': ['A3', 'A4']}
  {'C01': ['A1'],
   'C02': ['A2', 'A6'],
   'C03': ['B1'],
   'C05': ['B3'],
   'C06': ['B2'],
   'C08': ['C1'],
-  'C10': ['C2'],
?     ^

+  'C11': ['C2'],
?     ^

   'C12': ['A3', 'A4']}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `boxoffice/booking.py` → `sort_events`: Sorting on (at, seq) looks like it could be just `at`, but seq is the file position, so events with the same timestamp (E01/E02) keep file order, as rule 1 requires. `at` is a parsed datetime, so the mixed formats sort correctly.
