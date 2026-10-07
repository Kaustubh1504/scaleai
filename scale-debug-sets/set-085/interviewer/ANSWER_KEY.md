# set-085 answer key: Referral payout review

**Domain:** fraud_detection  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_signals.TestSignals.test_1_rings` | B1 Device ids not case-folded |
| `test_2_report.TestReport.test_2_flags` | B2 Burst gap uses the seconds field |
| `test_2_report.TestReport.test_3_payouts` | B3 Bonus paid per deposit, not per account |

## Failing pattern with all bugs present

- `tests.test_1_signals.TestSignals.test_1_rings`
- `tests.test_2_report.TestReport.test_2_flags`
- `tests.test_2_report.TestReport.test_3_payouts`

## Bugs (recommended order)

### B1: Device ids not case-folded

- **Type:** id-normalization
- **Symptom:** Test 1 test_1_rings: the ring [acc-06, acc-28, acc-29] comes back as [acc-06, acc-28] (acc-29 missing), so it drops behind [acc-03, acc-16] in the ordering. Self-referrals, flags and payouts are unchanged.
- **Location:** `refwatch/loader.py` → `clean_device`
- **Why it fails:** acc-29's device is written `dv-60` while acc-06 and acc-28 have `DV-60`. Without upper-casing, the device keys differ, so acc-29 is never linked and the three-account ring shrinks to two. The self-referral acc-06 -> acc-28 survives because those two still match, so nothing downstream changes.
- **Failing test:** `test_1_signals.TestSignals.test_1_rings`
- **Unblocks:** test_1_rings.

Fix:

```diff
-    return (raw or "").strip() or None
+    return (raw or "").strip().upper() or None
```

Observed with only this bug applied (`tests.test_1_signals.TestSignals.test_1_rings`):

```
AssertionError: Lists differ: [['acc-03', 'acc-16'], ['acc-06', 'acc-28'], ['acc-07', 'acc-08']] != [['acc-06', 'acc-28', 'acc-29'], ['acc-03', 'acc-16'], ['acc-07', 'acc-08']]

First differing element 0:
['acc-03', 'acc-16']
['acc-06', 'acc-28', 'acc-29']

- [['acc-03', 'acc-16'], ['acc-06', 'acc-28'], ['acc-07', 'acc-08']]
+ [['acc-06', 'acc-28', 'acc-29'], ['acc-03', 'acc-16'], ['acc-07', 'acc- ...
```

### B2: Burst gap uses the seconds field

- **Type:** timedelta-seconds
- **Symptom:** Test 2 test_2_flags: acc-03 gets ['self_referral', 'burst'] instead of ['self_referral']. Every other referrer's flags, the held list and releasable_usd are unchanged.
- **Location:** `refwatch/timeutil.py` → `minutes_between`
- **Why it fails:** `timedelta.seconds` is only the seconds part after whole days are removed. acc-03's referrals signed up at 10:00, 10:20 and 10:40 on three different days, so the span reads as 40 minutes and acc-03 gets a `burst` flag. acc-03 is already held for its self-referral, so the held list and totals do not move; only its flags do.
- **Failing test:** `test_2_report.TestReport.test_2_flags`
- **Unblocks:** test_2_flags.

Fix:

```diff
-    return (later - earlier).seconds / 60
+    return (later - earlier).total_seconds() / 60
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_2_flags`):

```
AssertionError: {'acc[45 chars]rral', 'burst'], 'acc-04': ['burst'], 'acc-05'[29 chars]al']} != {'acc[45 chars]rral'], 'acc-04': ['burst'], 'acc-05': [], 'ac[20 chars]al']}
  {'acc-01': [],
   'acc-02': [],
-  'acc-03': ['self_referral', 'burst'],
?                            ---------

+  'acc-03': ['self_referral'],
   'acc-04': ['burst'],
   'acc-05': [],
   'acc-06': ['self_referral']}
```

### B3: Bonus paid per deposit, not per account

- **Type:** missing-dedupe
- **Symptom:** Test 2 test_3_payouts: acc-04 shows payout_usd 75 instead of 50; all other payouts match. Its qualifying count (2), the held list, releasable_usd (150) and top_referrer are unchanged.
- **Location:** `refwatch/rules.py` → `bonus_ledger`
- **Why it fails:** The `paid` set is checked but never filled, so a referred account with two qualifying deposits earns its referrer two bonuses. acc-19 deposited twice (d10, d11), so acc-04 shows 75 instead of 50. acc-04 is held for its burst, so releasable_usd and top_referrer are unchanged and the qualifying count (a set) still says 2.
- **Failing test:** `test_2_report.TestReport.test_3_payouts`
- **Unblocks:** test_3_payouts.

Fix:

```diff
+        paid.add(acct.id)
         ledger.append(
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_3_payouts`):

```
AssertionError: {'acc[15 chars]02': 50, 'acc-03': 25, 'acc-04': 75, 'acc-05': 50, 'acc-06': 0} != {'acc[15 chars]02': 50, 'acc-03': 25, 'acc-04': 50, 'acc-05': 50, 'acc-06': 0}
  {'acc-01': 50,
   'acc-02': 50,
   'acc-03': 25,
-  'acc-04': 75,
?            -

+  'acc-04': 50,
?             +

   'acc-05': 50,
   'acc-06': 0}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `refwatch/timeutil.py` → `within_days`: The spec makes the 14-day window inclusive at both ends (deposit at or after signup, exactly 14 days later still counts), which is exactly `timedelta(0) <= end - start <= timedelta(days=days)`. acc-25's deposit lands exactly 14 days after signup and must qualify; acc-26's lands 14 days and 1 hour later and must not. The `<=` looks like the classic boundary suspect but is correct.
- `refwatch/links.py` → `find`: Union-find with path halving: `parent[x] = parent[parent[x]]` points x at its grandparent before stepping, which only shortens paths and never changes which root a node reaches. It looks like it could skip or corrupt roots, but the root is the only node with parent[x] == x and the loop stops there.
