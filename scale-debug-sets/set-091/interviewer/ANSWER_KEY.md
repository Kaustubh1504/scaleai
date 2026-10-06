# set-091 answer key: Workshop seat holds: hold window, tier priority, seats left

**Domain:** seat_reservation  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_allocation.TestAllocation.test_contested_sessions_follow_tier` | B1 members.csv read without stripping the BOM |
| `test_1_allocation.TestAllocation.test_expired_holds` | B2 Confirmation at exactly 15 minutes treated as late |
| `test_2_report.TestSummary.test_seats_left` | B3 Counter subtraction drops sold-out sessions |

## Failing pattern with all bugs present

- `tests.test_1_allocation.TestAllocation.test_contested_sessions_follow_tier`
- `tests.test_1_allocation.TestAllocation.test_expired_holds`
- `tests.test_2_report.TestSummary.test_seats_left`

## Bugs (recommended order)

### B1: members.csv read without stripping the BOM

- **Type:** csv-bom-encoding
- **Symptom:** Test 1 test_contested_sessions_follow_tier: A2 books H04+H05 and waitlists gold member m-07's H06; C2 books H16 and waitlists gold member m-12's H15. Seat totals are unchanged, so nothing else fails.
- **Location:** `seatbook/loader.py` → `read_rows`
- **Why it fails:** With plain utf-8 the BOM stays glued to the first header, so the column is named '\ufefftier'. row.get("tier") returns None for every member, everyone falls back to standard, and contested sessions are ordered by time only.
- **Failing test:** `test_1_allocation.TestAllocation.test_contested_sessions_follow_tier`
- **Unblocks:** test_contested_sessions_follow_tier.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_1_allocation.TestAllocation.test_contested_sessions_follow_tier`):

```
AssertionError: {'A2': (['H04', 'H05'], ['H06']), 'C2': (['H16'], ['H15'])} != {'A2': (['H04', 'H06'], ['H05']), 'C2': (['H15'], ['H16'])}
- {'A2': (['H04', 'H05'], ['H06']), 'C2': (['H16'], ['H15'])}
+ {'A2': (['H04', 'H06'], ['H05']), 'C2': (['H15'], ['H16'])}
```

### B2: Confirmation at exactly 15 minutes treated as late

- **Type:** time-window-boundary
- **Symptom:** Test 1 test_expired_holds: H08 appears in the expired list (['H03', 'H08', 'H10', 'H17', 'H23']). B1's booked seats don't change because H08 was going to be waitlisted anyway.
- **Location:** `seatbook/holds.py` → `is_confirmed`
- **Why it fails:** The spec says a confirmation at exactly 15 minutes is still in time. `<` makes the deadline itself exclusive, so H08 (placed 10:01, confirmed 10:16:00) expires.
- **Failing test:** `test_1_allocation.TestAllocation.test_expired_holds`
- **Unblocks:** test_expired_holds.

Fix:

```diff
-    return hold.confirmed_at < deadline
+    return hold.confirmed_at <= deadline
```

Observed with only this bug applied (`tests.test_1_allocation.TestAllocation.test_expired_holds`):

```
AssertionError: Lists differ: ['H03', 'H08', 'H10', 'H17', 'H23'] != ['H03', 'H10', 'H17', 'H23']

First differing element 1:
'H08'
'H10'

First list contains 1 additional elements.
First extra element 4:
'H23'

- ['H03', 'H08', 'H10', 'H17', 'H23']
?         -------

+ ['H03', 'H10', 'H17', 'H23']
```

### B3: Counter subtraction drops sold-out sessions

- **Type:** counter-misuse
- **Symptom:** Test 2 test_seats_left: seats_left only lists A1, C2, D1, E1, E2. Every session with 0 seats left (A2, B1, B2, C1, D2) is missing.
- **Location:** `seatbook/reports.py` → `summarize`
- **Why it fails:** Counter subtraction keeps only positive results, so every session with 0 seats left (sold out or closed) disappears from seats_left. The spec wants every session listed.
- **Failing test:** `test_2_report.TestSummary.test_seats_left`
- **Unblocks:** test_seats_left.

Fix:

```diff
-    seats_left = dict(sorted((capacity - booked).items()))
+    seats_left = {sid: capacity[sid] - booked[sid] for sid in sorted(capacity)}
```

Observed with only this bug applied (`tests.test_2_report.TestSummary.test_seats_left`):

```
AssertionError: {'A1': 2, 'C2': 1, 'D1': 7, 'E1': 2, 'E2': 1} != {'A1': 2, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': [33 chars]': 1}
- {'A1': 2, 'C2': 1, 'D1': 7, 'E1': 2, 'E2': 1}
+ {'A1': 2,
+  'A2': 0,
+  'B1': 0,
+  'B2': 0,
+  'C1': 0,
+  'C2': 1,
+  'D1': 7,
+  'D2': 0,
+  'E1': 2,
+  'E2': 1}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `seatbook/allocation.py` → `priority_key`: The minus on the rank looks like a flipped priority, but sorting ascending on -rank puts the highest rank (gold, 3) first, which is what the spec wants because the higher number is more important. Then earliest placed_at, then hold_id.
- `seatbook/loader.py` → `parse_when`: The `%d.%m.%Y` format looks like a day/month swap, but the README says the dotted format is day.month.year. It covers exactly the three listed formats and returns None for a blank cell.
