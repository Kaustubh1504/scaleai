# set-071 answer key: Weekly contributor payouts with adjustments and carryover

**Domain:** payouts  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_statements.TestStatements.test_adjustments`
- `tests.test_1_statements.TestStatements.test_lines_and_earned`
- `tests.test_1_statements.TestStatements.test_unmatched_adjustments`
- `tests.test_2_payouts.TestPayouts.test_paid_and_held`
- `tests.test_2_payouts.TestPayouts.test_settlement`
- `tests.test_2_payouts.TestPayouts.test_total_paid`

## Bugs (recommended order)

### B1: Byte-order mark kept in the first header

- **Type:** csv-bom-encoding
- **Symptom:** Test 1: every bonus/clawback is (0, 0) and unmatched_adjustments is 10 instead of 1. Test 2: settlement drops all adjustments (C01 gross 2298 instead of 3798, C04 1588 instead of 338), C10 and C12 fall below the minimum and total_paid is 4934 instead of 12165.
- **Location:** `payrun/loader.py` → `_rows`
- **Why it fails:** adjustments.csv starts with a UTF-8 byte-order mark. Read as plain utf-8, the first header becomes '\ufeffcontributor_id' (strip() does not remove U+FEFF), so row.get('contributor_id') is '' for every row and every adjustment is treated as unmatched.
- **Unblocks:** Test 1 adjustments and unmatched count, and part of Test 2. It exposes B2.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_1_statements.TestStatements.test_adjustments`):

```
AssertionError: {'C01': (0, 0), 'C02': (0, 0), 'C03': (0, 0), 'C04[95 chars], 0)} != {'C01': (1500, 0), 'C02': (0, 410), 'C03': (500, 0[115 chars], 0)}
- {'C01': (0, 0),
+ {'C01': (1500, 0),
?          +++

-  'C02': (0, 0),
+  'C02': (0, 410),
?             ++

-  'C03': (0, 0),
+  'C03': (500, 0),
?          ++

-  'C04': (0, 0),
+  'C04': (0, 1250),
?             +++

   'C06': (0, 0),
-  'C07' ...
```

### B2: Adjustment totals shared between contributors

- **Type:** mutable-default
- **Symptom:** Only visible after B1 is fixed. Test 1: adjustments become running totals down the sorted roster (C02 (1500, 410), C03 (2000, 410), C04 (2000, 1660) ...). Test 2 is worse still because the totals carry over from Test 1's build_report call: every contributor clears the minimum and total_paid is 54024.
- **Location:** `payrun/ledger.py` → `adjustment_totals`
- **Why it fails:** The default dict is created once when the function is defined, so every call without `totals` adds into the same dict. Each statement gets the running total of every contributor processed before it (and of earlier build_report calls).
- **Unblocks:** Test 1 adjustments and Test 2 settlement.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-def adjustment_totals(adjustments, totals={"bonus": 0, "clawback": 0}):
+def adjustment_totals(adjustments, totals=None):
+    if totals is None:
+        totals = {"bonus": 0, "clawback": 0}
```

Observed with only this bug applied (`tests.test_1_statements.TestStatements.test_adjustments`):

```
AssertionError: {'C01[17 chars]2': (1500, 410), 'C03': (2000, 410), 'C04': (2[132 chars]035)} != {'C01[17 chars]2': (0, 410), 'C03': (500, 0), 'C04': (0, 1250[97 chars], 0)}
  {'C01': (1500, 0),
-  'C02': (1500, 410),
?          ---

+  'C02': (0, 410),
-  'C03': (2000, 410),
?          ^^    --

+  'C03': (500, 0),
?          ^

-  'C04': (2000, 1660),
?          ---    ^^

+  'C04': (0, 1250),
? ...
```

### B3: Every status treated as payable

- **Type:** or-precedence
- **Symptom:** Test 1: lines/earned include rejected and pending entries (C01 (4, 2658), C02 (3, 1755), C07 (3, 1635), C08 (3, 1434), C10 (2, 175)). Test 2: C07 is now paid, and total_paid is 14985 instead of 12165.
- **Location:** `payrun/rules.py` → `is_payable`
- **Why it fails:** `a == b or "auto-approved"` parses as `(a == b) or "auto-approved"`, and a non-empty string is truthy, so rejected and pending entries are paid too.
- **Unblocks:** Test 1 lines/earned and Test 2 settlement.

Fix:

```diff
-    return entry.status == "approved" or "auto-approved"
+    return entry.status in ("approved", "auto-approved")
```

Observed with only this bug applied (`tests.test_1_statements.TestStatements.test_lines_and_earned`):

```
AssertionError: {'C01': (4, 2658), 'C02': (3, 1755), 'C03': (1, 75[123 chars]656)} != {'C01': (3, 2298), 'C02': (2, 1205), 'C03': (1, 75[120 chars]656)}
- {'C01': (4, 2658),
?          ^   ^^

+ {'C01': (3, 2298),
?          ^   ^^

-  'C02': (3, 1755),
?          ^   ^^

+  'C02': (2, 1205),
?          ^   ^^

   'C03': (1, 750),
-  'C04': (3, 2358),
?          ^   ^^

+  'C04': (2, 2088),
?      ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `payrun/rules.py` → `in_period`: The `<` against midnight of end + 1 day looks like it drops the end date, but it is exactly what makes the whole end date (up to 23:59:59) count while 00:10 the next day does not. The spec says both dates are included in full.
- `payrun/rules.py` → `pct_of`: `(cents * pct + 50) // 100` looks like integer-division truncation, but adding 50 before dividing by 100 is integer half-up rounding. Replacing it with round() would use banker's rounding and turn C02's 544.5 into 544.
