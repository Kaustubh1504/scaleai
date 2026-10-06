# set-047 answer key: Pay-period statements with bonuses and a platform fee

**Domain:** payouts  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_earnings.TestEarnings.test_1_base_earnings` | B1 Period end treated as inclusive |
| `test_1_earnings.TestEarnings.test_2_bonuses` | B2 Byte order mark kept in the first header |
| `test_2_statement.TestStatement.test_3_fees_on_task_only_earners` | B3 Fee rounded with banker's rounding |

## Failing pattern with all bugs present

- `tests.test_1_earnings.TestEarnings.test_1_base_earnings`
- `tests.test_1_earnings.TestEarnings.test_2_bonuses`
- `tests.test_2_statement.TestStatement.test_3_fees_on_task_only_earners`

## Bugs (recommended order)

### B1: Period end treated as inclusive

- **Type:** time-window-boundary
- **Symptom:** Test 1 test_1_base_earnings: C-01 base_cents is 860 instead of 650 (T-107, a 210-cent transcribe task at exactly 2026-04-15 00:00, is paid). Every other contributor matches.
- **Location:** `paycycle/earnings.py` → `in_period`
- **Why it fails:** The period is half-open. T-107 was completed at exactly 2026-04-15 00:00, which is the next period's start, so it must not be paid now.
- **Failing test:** `test_1_earnings.TestEarnings.test_1_base_earnings`
- **Unblocks:** test_1_base_earnings

Fix:

```diff
-    return period["start"] <= ts <= period["end"]
+    return period["start"] <= ts < period["end"]
```

Observed with only this bug applied (`tests.test_1_earnings.TestEarnings.test_1_base_earnings`):

```
AssertionError: {'C-01': 860, 'C-02': 295, 'C-03': 1060, 'C-04': 3[39 chars] 220} != {'C-01': 650, 'C-02': 295, 'C-03': 1060, 'C-04': 3[39 chars] 220}
- {'C-01': 860,
?          -

+ {'C-01': 650,
?           +

   'C-02': 295,
   'C-03': 1060,
   'C-04': 325,
   'C-05': 1220,
   'C-06': 1425,
   'C-07': 220}
```

### B2: Byte order mark kept in the first header

- **Type:** csv-bom-encoding
- **Symptom:** Test 1 test_2_bonuses: every bonus_cents is 0 and C-08/C-09 disappear from the statement entirely; task earnings are unaffected.
- **Location:** `paycycle/loader.py` → `_rows`
- **Why it fails:** bonuses.csv starts with a UTF-8 BOM. Read as plain utf-8, the first header becomes '\ufeffcontributor_id' (strip() does not remove it), so `r.get("contributor_id")` is None and every bonus row is skipped as having no id.
- **Failing test:** `test_1_earnings.TestEarnings.test_2_bonuses`
- **Unblocks:** test_2_bonuses

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_1_earnings.TestEarnings.test_2_bonuses`):

```
AssertionError: {'C-01': 0, 'C-02': 0, 'C-03': 0, 'C-04': 0, 'C-05[22 chars]': 0} != {'C-01': 1725, 'C-02': 2675, 'C-03': 0, 'C-04': 0,[60 chars] 400}
- {'C-01': 0, 'C-02': 0, 'C-03': 0, 'C-04': 0, 'C-05': 0, 'C-06': 0, 'C-07': 0}
+ {'C-01': 1725,
+  'C-02': 2675,
+  'C-03': 0,
+  'C-04': 0,
+  'C-05': 0,
+  'C-06': 1000,
+  'C-07': 750,
+  'C-08': 3000,
+  'C-09': 400}
```

### B3: Fee rounded with banker's rounding

- **Type:** float-rounding
- **Symptom:** Test 2 test_3_fees_on_task_only_earners: C-03 shows (26, 1034) instead of (27, 1033) and C-05 (30, 1190) instead of (31, 1189). C-04 is unchanged.
- **Location:** `paycycle/statement.py` → `platform_fee`
- **Why it fails:** Python's round() rounds halves to the even neighbour, so 26.5 → 26 and 30.5 → 30. The spec rounds halves up.
- **Failing test:** `test_2_statement.TestStatement.test_3_fees_on_task_only_earners`
- **Unblocks:** test_3_fees_on_task_only_earners

Fix:

```diff
-    return round(gross_cents * fee_percent / 100)
+    basis_points = int(round(fee_percent * 100))
+    return (gross_cents * basis_points + 5000) // 10000
```

Observed with only this bug applied (`tests.test_2_statement.TestStatement.test_3_fees_on_task_only_earners`):

```
AssertionError: {'C-03': (26, 1034), 'C-04': (8, 317), 'C-05': (30, 1190)} != {'C-03': (27, 1033), 'C-04': (8, 317), 'C-05': (31, 1189)}
- {'C-03': (26, 1034), 'C-04': (8, 317), 'C-05': (30, 1190)}
?            ^     ^                               ^     -

+ {'C-03': (27, 1033), 'C-04': (8, 317), 'C-05': (31, 1189)}
?            ^     ^                               ^    +
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `paycycle/utils.py` → `to_cents`: Multiplying a Decimal after quantize looks like it could leave fractions, but quantize to 0.01 guarantees a whole number of cents, it rounds half up as the spec says, and it strips `$` and thousands separators. Blank amounts return None so the loader can skip them.
