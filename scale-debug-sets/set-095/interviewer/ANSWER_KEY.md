# set-095 answer key: Weekly payout file with speed audit

**Domain:** payouts  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_statements.TestStatements.test_1_adjustments_and_net` | B1 Adjustment ids are not upper-cased |
| `test_2_payfile.TestPayfile.test_2_audit_flags` | B2 Audit runs over every work entry |
| `test_2_payfile.TestPayfile.test_3_payout_file` | B3 Account numbers kept as text |

## Failing pattern with all bugs present

- `tests.test_1_statements.TestStatements.test_1_adjustments_and_net`
- `tests.test_2_payfile.TestPayfile.test_2_audit_flags`
- `tests.test_2_payfile.TestPayfile.test_3_payout_file`

## Bugs (recommended order)

### B1: Adjustment ids are not upper-cased

- **Type:** id-normalization
- **Symptom:** test_1_adjustments_and_net fails: C-01 shows adjustments 0.00 and net 7.50 instead of -1.20 and 6.30. Every other contributor matches, and C-01 is held either way, so no other test changes.
- **Location:** `paycalc/loader.py` → `load_adjustments`
- **Why it fails:** The adjustments file writes C-01 as `c-01`. Without upper-casing, the clawback is keyed under `c-01`, which is not a roster id, so build_statements never adds it to C-01.
- **Failing test:** `test_1_statements.TestStatements.test_1_adjustments_and_net`
- **Unblocks:** test_1_adjustments_and_net

Fix:

```diff
-    return [(clean(a["contributor_id"]), parse_amount(a["amount"])) for a in raw["adjustments"]]
+    return [(clean(a["contributor_id"]).upper(), parse_amount(a["amount"])) for a in raw["adjustments"]]
```

Observed with only this bug applied (`tests.test_1_statements.TestStatements.test_1_adjustments_and_net`):

```
AssertionError: {'C-01': ('0.00', '7.50'), 'C-02': ('5.00', '14.00')[213 chars]00')} != {'C-01': ('-1.20', '6.30'), 'C-02': ('5.00', '14.00'[214 chars]00')}
- {'C-01': ('0.00', '7.50'),
?            ^ ^     ^ ^

+ {'C-01': ('-1.20', '6.30'),
?            ^^ ^     ^ ^

   'C-02': ('5.00', '14.00'),
   'C-03': ('0.25', '5.95'),
   'C-04': ('-0.60', '5.86'),
   'C-05': ('0.00', '5.19'),
   'C-06': (' ...
```

### B2: Audit runs over every work entry

- **Type:** counting-wrong-subset
- **Symptom:** test_2_audit_flags fails: flags are {'C-02': ['fast:gale', 'fast:helix'], 'C-05': ['fast:ember'], 'C-11': ['fast:cirrus']} instead of {'C-02': ['fast:helix'], 'C-05': ['fast:ember']}.
- **Location:** `paycalc/payfile.py` → `build_report`
- **Why it fails:** build_report hands the raw work log to audit_flags instead of the payable entries, so a rejected entry (w09) and a contributor who is not on the roster (C-11) get flagged.
- **Failing test:** `test_2_payfile.TestPayfile.test_2_audit_flags`
- **Unblocks:** test_2_audit_flags

Fix:

```diff
-        "flags": audit_flags(work, rates),
+        "flags": audit_flags(entries, rates),
```

Observed with only this bug applied (`tests.test_2_payfile.TestPayfile.test_2_audit_flags`):

```
AssertionError: {'C-02': ['fast:gale', 'fast:helix'], 'C-05': ['fast:embe[24 chars]us']} != {'C-02': ['fast:helix'], 'C-05': ['fast:ember']}
+ {'C-02': ['fast:helix'], 'C-05': ['fast:ember']}
- {'C-02': ['fast:gale', 'fast:helix'],
-  'C-05': ['fast:ember'],
-  'C-11': ['fast:cirrus']}
```

### B3: Account numbers kept as text

- **Type:** string-vs-int
- **Symptom:** test_3_payout_file fails: the lines are right but ordered 104433, 230111, 61005, 830 instead of 830, 61005, 104433, 230111.
- **Location:** `paycalc/loader.py` → `load_contributors`
- **Why it fails:** account_no stays a string, so payout_lines sorts the paid contributors lexicographically: "104433" < "230111" < "61005" < "830". The lines themselves look identical because the numbers have no leading zeros.
- **Failing test:** `test_2_payfile.TestPayfile.test_3_payout_file`
- **Unblocks:** test_3_payout_file

Fix:

```diff
-            clean(row["account_no"]), clean(row["method"]).lower())
+            int(clean(row["account_no"])), clean(row["method"]).lower())
```

Observed with only this bug applied (`tests.test_2_payfile.TestPayfile.test_3_payout_file`):

```
AssertionError: Lists differ: ['104433,wire,14.00', '230111,paypal,10.20'[37 chars].00'] != ['830,ach,10.00', '61005,paypal,1009.00', '[37 chars].20']

First differing element 0:
'104433,wire,14.00'
'830,ach,10.00'

+ ['830,ach,10.00',
- ['104433,wire,14.00',
-  '230111,paypal,10.20',
   '61005,paypal,1009.00',
-  '830,ach,10.00']
+  '104433,wire,14.00',
+  '230111,paypal,10.20']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `paycalc/loader.py` → `parse_amount`: The parenthesised-negative branch looks like it could drop the sign or choke on `$`/`,`, but it strips `$` and `,` first and returns -Decimal for `(1.20)`, exactly as the spec says. It is the obvious suspect for C-01's missing clawback, but the value is parsed fine; the id never matches.
- `paycalc/earnings.py` → `in_period`: Comparing a date with `< period.end` looks like it drops the last day, but the spec makes the period half-open: w14 at 2026-09-28 00:00 belongs to the next week and w05 at 09-27 23:59 counts.
