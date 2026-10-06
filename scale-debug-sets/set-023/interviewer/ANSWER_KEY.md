# set-023 answer key: Contributor payout run with late penalties and FX

**Domain:** payouts  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_task_pay.TestTaskPay.test_late_submissions` | B1 Elapsed hours drop whole days |
| `test_2_payout_report.TestPayoutReport.test_local_currency_payouts` | B2 Currency conversion truncates |
| `test_2_payout_report.TestPayoutReport.test_top_contributors` | B3 Counter.update on an id string |

## Failing pattern with all bugs present

- `tests.test_1_task_pay.TestTaskPay.test_late_submissions`
- `tests.test_2_payout_report.TestPayoutReport.test_local_currency_payouts`
- `tests.test_2_payout_report.TestPayoutReport.test_top_contributors`

## Bugs (recommended order)

### B1: Elapsed hours drop whole days

- **Type:** timedelta-seconds
- **Symptom:** test_late_submissions fails: T106 pays 1150 and T121 pays 2700 (full price) instead of 575 and 1350. T113 is 45 either way.
- **Location:** `payroll/utils.py` → `hours_between`
- **Why it fails:** timedelta.seconds is only the seconds part after whole days are taken out. T106 (26 h) reads as 2 h and T121 (74 h) as 2 h, so neither is treated as late.
- **Failing test:** `test_1_task_pay.TestTaskPay.test_late_submissions`
- **Unblocks:** test_late_submissions

Fix:

```diff
-    return (end - start).seconds / 3600
+    return (end - start).total_seconds() / 3600
```

Observed with only this bug applied (`tests.test_1_task_pay.TestTaskPay.test_late_submissions`):

```
AssertionError: {'T106': 1150, 'T113': 45, 'T121': 2700} != {'T106': 575, 'T113': 45, 'T121': 1350}
- {'T106': 1150, 'T113': 45, 'T121': 2700}
?          -- ^                      ^^^

+ {'T106': 575, 'T113': 45, 'T121': 1350}
?           ^^                      ^^^
```

### B2: Currency conversion truncates

- **Type:** float-rounding
- **Symptom:** test_local_currency_payouts fails: C01 gets EUR 878 instead of 879, and C04 gets INR 116339 instead of 116340. Other currencies match.
- **Location:** `payroll/pricing.py` → `to_local`
- **Why it fails:** int() truncates. C01's 955 × 0.92 = 878.6 should round to 879, and C04's 1400 × 83.1 comes out as 116339.99999999999 in floating point, which truncates to 116339 instead of 116340.
- **Failing test:** `test_2_payout_report.TestPayoutReport.test_local_currency_payouts`
- **Unblocks:** test_local_currency_payouts

Fix:

```diff
-    return int(usd_cents * float(rates["currency_rates"][currency]))
+    return round(usd_cents * float(rates["currency_rates"][currency]))
```

Observed with only this bug applied (`tests.test_2_payout_report.TestPayoutReport.test_local_currency_payouts`):

```
AssertionError: {'C01': ('EUR', 878), 'C04': ('INR', 116339), 'C05': ('GBP'[88 chars], 0)} != {'C01': ('EUR', 879), 'C04': ('INR', 116340), 'C05': ('GBP'[88 chars], 0)}
- {'C01': ('EUR', 878),
?                   ^

+ {'C01': ('EUR', 879),
?                   ^

-  'C04': ('INR', 116339),
?                     ^^

+  'C04': ('INR', 116340),
?                     ^^

   'C05': ('GBP', 995),
   'C07 ...
```

### B3: Counter.update on an id string

- **Type:** counter-misuse
- **Symptom:** test_top_contributors fails: the list is [['C', 26], ['0', 22], ['1', 10]] instead of [['C06', 4], ['C02', 3], ['C04', 3]].
- **Location:** `payroll/reports.py` → `build_report`
- **Why it fails:** Counter.update iterates its argument, so a string like 'C06' adds one count each for 'C', '0' and '6'. The top list ends up made of characters.
- **Failing test:** `test_2_payout_report.TestPayoutReport.test_top_contributors`
- **Unblocks:** test_top_contributors

Fix:

```diff
-        counts.update(task.contributor_id)
+        counts[task.contributor_id] += 1
```

Observed with only this bug applied (`tests.test_2_payout_report.TestPayoutReport.test_top_contributors`):

```
AssertionError: Lists differ: [['C', 26], ['0', 22], ['1', 10]] != [['C06', 4], ['C02', 3], ['C04', 3]]

First differing element 0:
['C', 26]
['C06', 4]

- [['C', 26], ['0', 22], ['1', 10]]
?        ^^         ^^     ^   ^^

+ [['C06', 4], ['C02', 3], ['C04', 3]]
?     ++   ^     + +   ^     ^^^   ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `payroll/pricing.py` → `base_pay`: The `//` looks like an integer-division slip, but rule 2 says per-minute pay is rounded down to a whole cent, and multiplying before dividing keeps it exact.
