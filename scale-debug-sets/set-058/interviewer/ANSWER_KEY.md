# set-058 answer key: Tenant rate limits and usage invoices

**Domain:** rate_limit_billing  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_limits.TestLimits.test_enterprise_not_throttled` | B1 Enterprise check compares the Plan enum to a string |
| `test_1_limits.TestLimits.test_window_boundary` | B2 Request exactly 60 s old still counted in the window |
| `test_1_limits.TestLimits.test_suspended_tenant` | B3 rpm_override 0 collapsed to None |
| `test_2_invoices.TestInvoices.test_credit_applied` | B4 Credit keys trimmed but not lower-cased |
| `test_2_invoices.TestInvoices.test_overage_part_cents` | B5 Overage part-cents floored instead of rounded up |
| `test_3_statement.TestStatement.test_top_tenants` | B6 Top tenants sorted quietest first |

## Failing pattern with all bugs present

- `tests.test_1_limits.TestLimits.test_enterprise_not_throttled`
- `tests.test_1_limits.TestLimits.test_suspended_tenant`
- `tests.test_1_limits.TestLimits.test_window_boundary`
- `tests.test_2_invoices.TestInvoices.test_credit_applied`
- `tests.test_2_invoices.TestInvoices.test_overage_part_cents`
- `tests.test_3_statement.TestStatement.test_top_tenants`

## Bugs (recommended order)

### B1: Enterprise check compares the Plan enum to a string

- **Type:** enum-vs-string
- **Symptom:** test_1_limits.test_enterprise_not_throttled: orbit has ['2026-05-01 14:00:40', '2026-05-01 14:00:50'] throttled instead of []. Its invoice is unchanged (flat enterprise fee).
- **Location:** `meterbill/limiter.py` → `limit_for`
- **Why it fails:** tenant.plan is a Plan member, and a plain Enum member never equals its value string ('enterprise'), so the enterprise branch never runs and orbit falls through to the plan's advisory rpm of 4.
- **Failing test:** `test_1_limits.TestLimits.test_enterprise_not_throttled`
- **Unblocks:** test_enterprise_not_throttled.

Fix:

```diff
-    if tenant.plan == Plan.ENTERPRISE.value:
+    if tenant.plan is Plan.ENTERPRISE:
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_enterprise_not_throttled`):

```
AssertionError: Lists differ: ['2026-05-01 14:00:40', '2026-05-01 14:00:50'] != []

First list contains 2 additional elements.
First extra element 0:
'2026-05-01 14:00:40'

- ['2026-05-01 14:00:40', '2026-05-01 14:00:50']
+ []
```

### B2: Request exactly 60 s old still counted in the window

- **Type:** time-window-boundary
- **Symptom:** test_1_limits.test_window_boundary: kestrel's throttled list is ['2026-05-01 10:01:00'] instead of ['2026-05-01 10:01:05'].
- **Location:** `meterbill/limiter.py` → `apply_limit`
- **Why it fails:** The window is (ts - 60s, ts], so a request exactly 60 s earlier must be evicted. With `>` it stays, kestrel's 10:01:00 request sees 3 in the window and is throttled; that frees a slot, so 10:01:05 is allowed instead.
- **Failing test:** `test_1_limits.TestLimits.test_window_boundary`
- **Unblocks:** test_window_boundary.

Fix:

```diff
-        while window and (ev.ts - window[0]).total_seconds() > WINDOW_S:
+        while window and (ev.ts - window[0]).total_seconds() >= WINDOW_S:
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_window_boundary`):

```
AssertionError: Lists differ: ['2026-05-01 10:01:00'] != ['2026-05-01 10:01:05']

First differing element 0:
'2026-05-01 10:01:00'
'2026-05-01 10:01:05'

- ['2026-05-01 10:01:00']
?                     ^

+ ['2026-05-01 10:01:05']
?                     ^
```

### B3: rpm_override 0 collapsed to None

- **Type:** falsy-zero
- **Symptom:** test_1_limits.test_suspended_tenant: ivory's throttled list is [] instead of all three of its requests.
- **Location:** `meterbill/loader.py` → `load_tenants`
- **Why it fails:** `or None` turns the real override 0 into 'no override', so suspended ivory is treated as an ordinary enterprise tenant with no limit.
- **Failing test:** `test_1_limits.TestLimits.test_suspended_tenant`
- **Unblocks:** test_suspended_tenant.

Fix:

```diff
-                rpm_override=parse_int(row["rpm_override"]) or None,
+                rpm_override=parse_int(row["rpm_override"]),
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_suspended_tenant`):

```
AssertionError: Lists differ: [] != ['2026-05-01 08:00:00', '2026-05-01 12:30:00', '2026-05-02 08:00:00']

Second list contains 3 additional elements.
First extra element 0:
'2026-05-01 08:00:00'

- []
+ ['2026-05-01 08:00:00', '2026-05-01 12:30:00', '2026-05-02 08:00:00']
```

### B4: Credit keys trimmed but not lower-cased

- **Type:** id-normalization
- **Symptom:** test_2_invoices.test_credit_applied: delta-labs shows credit_cents 0 and amount_cents 3000 (expected 1500 / 1500).
- **Location:** `meterbill/loader.py` → `load_credits`
- **Why it fails:** credits.json has ' Delta-Labs '. clean() strips it to 'Delta-Labs', which doesn't match the tenant id 'delta-labs', so credits.get falls back to 0.
- **Failing test:** `test_2_invoices.TestInvoices.test_credit_applied`
- **Unblocks:** test_credit_applied.

Fix:

```diff
-    return {clean(k): int(v) for k, v in raw.items()}
+    return {norm_id(k): int(v) for k, v in raw.items()}
```

Observed with only this bug applied (`tests.test_2_invoices.TestInvoices.test_credit_applied`):

```
AssertionError: {'pla[27 chars]gross_cents': 3000, 'credit_cents': 0, 'amount_cents': 3000} != {'pla[27 chars]gross_cents': 3000, 'credit_cents': 1500, 'amount_cents': 1500}
- {'amount_cents': 3000,
?                  ^^

+ {'amount_cents': 1500,
?                  ^^

-  'credit_cents': 0,
+  'credit_cents': 1500,
?                  +++

   'gross_cents': 3000,
   'plan': 'pro',
   'units': 1400}
```

### B5: Overage part-cents floored instead of rounded up

- **Type:** integer-division
- **Symptom:** test_2_invoices.test_overage_part_cents: harbor shows gross_cents 3200 and amount_cents 3000 (expected 3201 / 3001).
- **Location:** `meterbill/billing.py` → `overage_cents`
- **Why it fails:** harbor's overage is 1203 units x 250 / 1000 = 300.75 cents. Floor division gives 300, but the spec rounds part-cents up to 301. The double negation is how the reference gets a ceiling from //.
- **Failing test:** `test_2_invoices.TestInvoices.test_overage_part_cents`
- **Unblocks:** test_overage_part_cents.

Fix:

```diff
-    return overage * terms.price_per_1k_cents // 1000
+    return -(-overage * terms.price_per_1k_cents // 1000)
```

Observed with only this bug applied (`tests.test_2_invoices.TestInvoices.test_overage_part_cents`):

```
AssertionError: {'pla[26 chars]'gross_cents': 3200, 'credit_cents': 200, 'amount_cents': 3000} != {'pla[26 chars]'gross_cents': 3201, 'credit_cents': 200, 'amount_cents': 3001}
- {'amount_cents': 3000,
?                     ^

+ {'amount_cents': 3001,
?                     ^

   'credit_cents': 200,
-  'gross_cents': 3200,
?                    ^

+  'gross_cents': 3201,
?                    ^

    ...
```

### B6: Top tenants sorted quietest first

- **Type:** sort-direction
- **Symptom:** test_3_statement.test_top_tenants: [['quill', 1], ['fjord', 2], ['acorn', 3]] instead of [['orbit', 6], ['brightpath', 5], ['kestrel', 5]].
- **Location:** `meterbill/reports.py` → `build_report`
- **Why it fails:** Without the minus the sort is ascending by request count, so the slice takes the three quietest tenants, despite the 'busiest first' comment.
- **Failing test:** `test_3_statement.TestStatement.test_top_tenants`
- **Unblocks:** test_top_tenants.

Fix:

```diff
-    top = sorted(requests, key=lambda t: (requests[t], t))[:TOP_N]
+    top = sorted(requests, key=lambda t: (-requests[t], t))[:TOP_N]
```

Observed with only this bug applied (`tests.test_3_statement.TestStatement.test_top_tenants`):

```
AssertionError: Lists differ: [['quill', 1], ['fjord', 2], ['acorn', 3]] != [['orbit', 6], ['brightpath', 5], ['kestrel', 5]]

First differing element 0:
['quill', 1]
['orbit', 6]

- [['quill', 1], ['fjord', 2], ['acorn', 3]]
+ [['orbit', 6], ['brightpath', 5], ['kestrel', 5]]
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `meterbill/utils.py` → `parse_ts`: Treating an all-digit string as epoch seconds and calling fromtimestamp looks like a timezone trap, but it passes tz=timezone.utc, and the two text formats get tzinfo=UTC too, so every timestamp is aware UTC and they compare and subtract consistently (1777633210 is 2026-05-01 11:00:10 UTC).
