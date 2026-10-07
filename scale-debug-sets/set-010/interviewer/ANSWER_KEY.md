# set-010 answer key: Tenant rate-limit audit and token invoices

**Domain:** rate_limit_billing  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_throttle.TestThrottle.test_retry_after` | B1 Retry-after left in milliseconds |
| `test_1_throttle.TestThrottle.test_throttled_requests` | B2 Request exactly 60 s old still counted |
| `test_2_usage.TestUsage.test_by_endpoint` | B3 groupby over unsorted rows |
| `test_3_invoices.TestInvoices.test_discounts` | B4 Explicit 0% discount replaced by plan default |
| `test_3_invoices.TestInvoices.test_overage` | B5 Overage blocks rounded instead of ceiled |
| `test_3_invoices.TestInvoices.test_top_tenants` | B6 Top tenants sorted ascending |

## Failing pattern with all bugs present

- `tests.test_1_throttle.TestThrottle.test_retry_after`
- `tests.test_1_throttle.TestThrottle.test_throttled_requests`
- `tests.test_2_usage.TestUsage.test_by_endpoint`
- `tests.test_3_invoices.TestInvoices.test_discounts`
- `tests.test_3_invoices.TestInvoices.test_overage`
- `tests.test_3_invoices.TestInvoices.test_top_tenants`

## Bugs (recommended order)

### B1: Retry-after left in milliseconds

- **Type:** ms-vs-s
- **Symptom:** Test 1 test_retry_after: {'R07': 35000, 'R11': 52000, 'R17': 55000, 'R22': 1} instead of {'R07': 35.0, 'R11': 52.0, 'R17': 55.0, 'R22': 0.001}.
- **Location:** `meterbill/limiter.py` → `replay`
- **Why it fails:** Timestamps and WINDOW_MS are milliseconds, but retry_after_s is specified in seconds. Without the `/ 1000` every value is 1000 times too large.
- **Failing test:** `test_1_throttle.TestThrottle.test_retry_after`
- **Unblocks:** test_1_throttle.TestThrottle.test_retry_after.

Fix:

```diff
-            throttled[req.request_id] = oldest + WINDOW_MS - req.ts_ms
+            throttled[req.request_id] = (oldest + WINDOW_MS - req.ts_ms) / 1000
```

Observed with only this bug applied (`tests.test_1_throttle.TestThrottle.test_retry_after`):

```
AssertionError: {'R07': 35000, 'R11': 52000, 'R17': 55000, 'R22': 1} != {'R07': 35.0, 'R11': 52.0, 'R17': 55.0, 'R22': 0.001}
- {'R07': 35000, 'R11': 52000, 'R17': 55000, 'R22': 1}
?           ^^            ^^            ^^

+ {'R07': 35.0, 'R11': 52.0, 'R17': 55.0, 'R22': 0.001}
?           ^            ^            ^          ++++
```

### B2: Request exactly 60 s old still counted

- **Type:** time-window-boundary
- **Symptom:** Test 1 test_throttled_requests: R03 (initech) is throttled too: ['R03', 'R07', 'R11', ...].
- **Location:** `meterbill/limiter.py` → `replay`
- **Why it fails:** initech's R03 arrives exactly 60 000 ms after R01. The spec says that request no longer counts, so only R02 is in the window and R03 is allowed. With `<=` R01 still counts and R03 is throttled.
- **Failing test:** `test_1_throttle.TestThrottle.test_throttled_requests`
- **Unblocks:** test_1_throttle.TestThrottle.test_throttled_requests.

Fix:

```diff
-        recent = [t for t in allowed[req.tenant] if req.ts_ms - t <= WINDOW_MS]
+        recent = [t for t in allowed[req.tenant] if req.ts_ms - t < WINDOW_MS]
```

Observed with only this bug applied (`tests.test_1_throttle.TestThrottle.test_throttled_requests`):

```
AssertionError: Lists differ: ['R03', 'R07', 'R11', 'R17', 'R18', 'R21', 'R22'] != ['R07', 'R11', 'R17', 'R18', 'R21', 'R22']

First differing element 0:
'R03'
'R07'

First list contains 1 additional elements.
First extra element 6:
'R22'

- ['R03', 'R07', 'R11', 'R17', 'R18', 'R21', 'R22']
?  -------

+ ['R07', 'R11', 'R17', 'R18', 'R21', 'R22']
```

### B3: groupby over unsorted rows

- **Type:** groupby-misuse
- **Symptom:** Test 2 test_by_endpoint: endpoint totals hold only the last day's tokens, e.g. acme chat 50000 instead of 150000, globex chat 400000 / embed 140000. monthly_tokens is still right.
- **Location:** `meterbill/usage.py` → `by_endpoint`
- **Why it fails:** itertools.groupby only groups consecutive equal keys. usage.csv is in date order, so the same (tenant, endpoint) shows up as several groups, and each assignment overwrites the last, leaving only the final day's tokens.
- **Failing test:** `test_2_usage.TestUsage.test_by_endpoint`
- **Unblocks:** test_2_usage.TestUsage.test_by_endpoint.

Fix:

```diff
+    rows = sorted(rows, key=lambda r: (r.tenant, r.endpoint))
     out = defaultdict(dict)
```

Observed with only this bug applied (`tests.test_2_usage.TestUsage.test_by_endpoint`):

```
AssertionError: {'acme': {'chat': 50000, 'embed': 62300}, 'globex': {'chat'[310 chars]000}} != {'acme': {'chat': 150000, 'embed': 62300}, 'globex': {'chat[314 chars]000}}
- {'acme': {'chat': 50000, 'embed': 62300},
+ {'acme': {'chat': 150000, 'embed': 62300},
?                   +

-  'globex': {'chat': 400000, 'embed': 140000},
?                     ^                ^

+  'globex': {'chat': 90000 ...
```

### B4: Explicit 0% discount replaced by plan default

- **Type:** falsy-zero
- **Symptom:** Test 3 test_discounts: umbrella gets a 15.95 discount instead of 0.0.
- **Location:** `meterbill/config.py` → `load_config`
- **Why it fails:** `pct or default` treats an explicit 0.0 like a missing value. umbrella is on enterprise (default 5%) with discount_pct 0, so it gets a 15.95 discount it should not have. tyrell is also 0 but on pro, whose default is 0, so it looks fine.
- **Failing test:** `test_3_invoices.TestInvoices.test_discounts`
- **Unblocks:** test_3_invoices.TestInvoices.test_discounts.

Fix:

```diff
-            discount_pct=pct or plan.default_discount_pct,
+            discount_pct=pct if pct is not None else plan.default_discount_pct,
```

Observed with only this bug applied (`tests.test_3_invoices.TestInvoices.test_discounts`):

```
AssertionError: {'acm[88 chars], 'tyrell': 0.0, 'umbrella': 15.95, 'wayne': 0.0, 'wonka': 0.0} != {'acm[88 chars], 'tyrell': 0.0, 'umbrella': 0.0, 'wayne': 0.0, 'wonka': 0.0}
  {'acme': 0.0,
   'globex': 35.9,
   'hooli': 21.2,
   'initech': 0.0,
   'soylent': 14.95,
   'stark': 10.95,
   'tyrell': 0.0,
-  'umbrella': 15.95,
?              ^^ ^^

+  'umbrella': 0.0,
?              ^ ^

   'wayne': ...
```

### B5: Overage blocks rounded instead of ceiled

- **Type:** float-rounding
- **Symptom:** Test 3 test_overage: acme's overage is 4.8 instead of 5.2.
- **Location:** `meterbill/billing.py` → `invoice`
- **Why it fails:** The spec bills every started block of 1 000 tokens. `round(12.3)` is 12, so acme's 12 300 excess tokens are billed as 12 blocks (4.80) instead of 13 (5.20). Every other tenant's excess is a whole number of thousands.
- **Failing test:** `test_3_invoices.TestInvoices.test_overage`
- **Unblocks:** test_3_invoices.TestInvoices.test_overage.

Fix:

```diff
# meterbill/billing.py
-    blocks = round(excess / 1000)
+    blocks = math.ceil(excess / 1000)

# meterbill/billing.py
+import math
```

Observed with only this bug applied (`tests.test_3_invoices.TestInvoices.test_overage`):

```
AssertionError: {'acme': 4.8, 'globex': 60.0, 'hooli': 125.0, 'ini[98 chars] 0.0} != {'acme': 5.2, 'globex': 60.0, 'hooli': 125.0, 'ini[98 chars] 0.0}
- {'acme': 4.8,
?          ^ ^

+ {'acme': 5.2,
?          ^ ^

   'globex': 60.0,
   'hooli': 125.0,
   'initech': 0.0,
   'soylent': 0.0,
   'stark': 24.0,
   'tyrell': 2.0,
   'umbrella': 20.0,
   'wayne': 4.0,
   'wonka': 0.0}
```

### B6: Top tenants sorted ascending

- **Type:** sort-direction
- **Symptom:** Test 3 test_top_tenants: ['initech', 'wayne', 'wonka'] instead of ['hooli', 'globex', 'umbrella'].
- **Location:** `meterbill/report.py` → `top_tenants`
- **Why it fails:** Without the minus sign the sort is ascending, so the first three are the cheapest invoices, not the most expensive.
- **Failing test:** `test_3_invoices.TestInvoices.test_top_tenants`
- **Unblocks:** test_3_invoices.TestInvoices.test_top_tenants.

Fix:

```diff
-    ranked = sorted(invoices.items(), key=lambda kv: (kv[1]["total"], kv[0]))
+    ranked = sorted(invoices.items(), key=lambda kv: (-kv[1]["total"], kv[0]))
```

Observed with only this bug applied (`tests.test_3_invoices.TestInvoices.test_top_tenants`):

```
AssertionError: Lists differ: ['initech', 'wayne', 'wonka'] != ['hooli', 'globex', 'umbrella']

First differing element 0:
'initech'
'hooli'

- ['initech', 'wayne', 'wonka']
+ ['hooli', 'globex', 'umbrella']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `meterbill/usage.py` → `in_period`: `row.day < end` looks like it drops the last day of the month, but `end` from period_bounds is the first day of the next month, so 30 April is included and 1 May is not.
- `meterbill/loader.py` → `parse_day`: It accepts exactly the two date formats in the README, with month/day order for the slash format.
