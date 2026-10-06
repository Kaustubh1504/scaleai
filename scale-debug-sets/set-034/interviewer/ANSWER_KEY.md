# set-034 answer key: Sliding-window rate limits and token overage billing

**Domain:** rate_limit_billing  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_limits.TestLimits.test_effective_limits`
- `tests.test_1_limits.TestLimits.test_throttled_requests`
- `tests.test_2_usage.TestUsage.test_allowed_and_throttled_counts`
- `tests.test_2_usage.TestUsage.test_billable_tokens`
- `tests.test_2_usage.TestUsage.test_by_endpoint`
- `tests.test_3_invoices.TestInvoices.test_invoice_amounts`
- `tests.test_3_invoices.TestInvoices.test_overage_tokens`
- `tests.test_3_invoices.TestInvoices.test_total_and_top_tenants`

## Bugs (recommended order)

### B1: Window left in milliseconds

- **Type:** ms-vs-s
- **Symptom:** Test 1 test_throttled_requests: acme [a04, a05, a06], cove [c03, c04], fern [f04, f05, f06], gale [g05, g06]. Test 2: acme allowed 3, billable tokens acme 1200 / fern 1800 / gale 8000. Test 3: acme 0.08, fern 0.32, gale 0.75; total 5.61.
- **Location:** `meterbill/plans.py` → `load_plans`
- **Why it fails:** Plan.window is compared with ages in seconds, but window_ms is milliseconds. Without the /1000 the window is 60,000 s (almost 17 hours), so every allowed request of the day stays in the window.
- **Unblocks:** Most of the throttling in Test 1, plus the allowed counts and tokens for acme, cove, fern and gale. Exposes B2.

Fix:

```diff
-            window=int(spec["window_ms"]),
+            window=int(spec["window_ms"]) / 1000,
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_throttled_requests`):

```
AssertionError: {'t-acme': ['a04', 'a05', 'a06'], 't-bolt': [], 't-cove'[153 chars]: []} != {'t-acme': ['a05'], 't-bolt': [], 't-cove': ['c03'], 't-[118 chars]: []}
- {'t-acme': ['a04', 'a05', 'a06'],
+ {'t-acme': ['a05'],
   't-bolt': [],
-  't-cove': ['c03', 'c04'],
?                  -------

+  't-cove': ['c03'],
   't-dune': [],
   't-echo': ['e01', 'e02'],
-  't-fern': ['f04', 'f05', 'f06'], ...
```

### B2: Request exactly one window old counted as inside

- **Type:** time-window-boundary
- **Symptom:** Only visible after B1 is fixed. Test 1: acme throttled [a04] instead of [a05]. Test 2: acme billable tokens 1900. Test 3: acme overage 900, amount 0.36, total 8.31.
- **Location:** `meterbill/limiter.py` → `SlidingWindowLimiter.allow`
- **Why it fails:** The window is (t - window, t], so a request exactly 60 s old has dropped out. `<=` keeps it, so acme's a04 (exactly 60 s after a01) sees 3 recent requests and is throttled, which then frees a slot for a05.
- **Unblocks:** acme's rows in Tests 1-3.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-if age_seconds(ts, prev) <= window]
+if age_seconds(ts, prev) < window]
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_throttled_requests`):

```
AssertionError: {'t-acme': ['a04'], 't-bolt': [], 't-cove': ['c03'], 't-[118 chars]: []} != {'t-acme': ['a05'], 't-bolt': [], 't-cove': ['c03'], 't-[118 chars]: []}
- {'t-acme': ['a04'],
?                ^

+ {'t-acme': ['a05'],
?                ^

   't-bolt': [],
   't-cove': ['c03'],
   't-dune': [],
   't-echo': ['e01', 'e02'],
   't-fern': ['f04', 'f05'],
   't-gale': ['g05'],
   't-hive': [] ...
```

### B3: Override of 0 falls back to the plan limit

- **Type:** falsy-zero
- **Symptom:** Test 1 test_effective_limits: t-echo 5 instead of 0, and echo throttles nothing. Test 2: echo allowed 2, tokens 7000, by_endpoint {/v1/chat: 2}. Test 3: echo overage 2000, amount 0.50, total 8.77.
- **Location:** `meterbill/plans.py` → `effective_limit`
- **Why it fails:** `override or plan.limit` treats a parsed 0 like a missing override, so the suspended tenant gets the growth plan's 5 requests per window.
- **Unblocks:** echo's rows in all three tests.

Fix:

```diff
-    return override or plan.limit
+    return plan.limit if override is None else override
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_effective_limits`):

```
AssertionError: {'t-a[54 chars]ho': 5, 't-fern': 3, 't-gale': 4, 't-hive': 10[22 chars]': 5} != {'t-a[54 chars]ho': 0, 't-fern': 3, 't-gale': 4, 't-hive': 10[22 chars]': 5}
  {'t-acme': 3,
   't-bolt': 5,
   't-cove': 2,
   't-dune': 10,
-  't-echo': 5,
?            ^

+  't-echo': 0,
?            ^

   't-fern': 3,
   't-gale': 4,
   't-hive': 10,
   't-iris': 3,
   't-jade': 5}
```

### B4: timedelta.seconds drops the days

- **Type:** timedelta-seconds
- **Symptom:** Test 1: bolt throttled [b06, b07] (its next-day requests). Test 2: bolt (5, 2), tokens 10000, chat 4 / embed 1. Test 3: bolt overage 5000, amount 1.25, total 7.09.
- **Location:** `meterbill/utils.py` → `age_seconds`
- **Why it fails:** `.seconds` is only the seconds component (0-86399) and ignores `.days`. bolt's requests a day apart look 10-50 s old, so the next-day burst is throttled as if it continued the previous day's window.
- **Unblocks:** bolt's rows in all three tests.

Fix:

```diff
-    return (now - then).seconds
+    return (now - then).total_seconds()
```

Observed with only this bug applied (`tests.test_1_limits.TestLimits.test_throttled_requests`):

```
AssertionError: {'t-a[21 chars]t': ['b06', 'b07'], 't-cove': ['c03'], 't-dune[114 chars]: []} != {'t-a[21 chars]t': [], 't-cove': ['c03'], 't-dune': [], 't-ec[102 chars]: []}
  {'t-acme': ['a05'],
-  't-bolt': ['b06', 'b07'],
+  't-bolt': [],
   't-cove': ['c03'],
   't-dune': [],
   't-echo': ['e01', 'e02'],
   't-fern': ['f04', 'f05'],
   't-gale': ['g05'],
   't-hive': [],
   't-iris': [],
   ' ...
```

### B5: Endpoint counter shared by every tenant

- **Type:** shared-class-attribute
- **Symptom:** Test 2 test_by_endpoint only: every tenant shows the same inflated counts (chat 40, embed 24 in a full run). The counter is shared across tenants and across build_report() calls, so the numbers depend on how many times the report was built.
- **Location:** `meterbill/usage.py` → `TenantUsage`
- **Why it fails:** A Counter defined on the class is one object shared by all instances, and `row.by_endpoint[...] += 1` mutates it in place. The int counters are fine because `+=` on an int rebinds an instance attribute.
- **Unblocks:** test_by_endpoint.

Fix:

```diff
     billable_tokens = 0
-    by_endpoint = Counter()
 
     def __init__(self, tenant_id):
         self.tenant_id = tenant_id
+        self.by_endpoint = Counter()
```

Observed with only this bug applied (`tests.test_2_usage.TestUsage.test_by_endpoint`):

```
AssertionError: {'t-a[14 chars]at': 40, '/v1/embed': 24}, 't-bolt': {'/v1/cha[380 chars] 24}} != {'t-a[14 chars]at': 3, '/v1/embed': 2}, 't-bolt': {'/v1/chat'[284 chars]: 1}}
- {'t-acme': {'/v1/chat': 40, '/v1/embed': 24},
?                         ^^                -

+ {'t-acme': {'/v1/chat': 3, '/v1/embed': 2},
?                         ^

-  't-bolt': {'/v1/chat': 40, '/v1/embed': 24},
?       ...
```

### B6: Banker's rounding on invoice amounts

- **Type:** float-rounding
- **Symptom:** Test 3 only: test_invoice_amounts shows bolt 2.42 and gale 2.92 (should be 2.43 / 2.93); total 8.25 instead of 8.27.
- **Location:** `meterbill/billing.py` → `charge`
- **Why it fails:** round() on a Decimal uses the context's ROUND_HALF_EVEN, so 2.425 → 2.42 and 2.925 → 2.92. The README rounds halves up.
- **Unblocks:** test_invoice_amounts and the total.
- **Masked:** only surfaces in test_3_invoices.

Fix:

```diff
-    return round(amount, 2)
+    return amount.quantize(CENT, rounding=ROUND_HALF_UP)
```

Observed with only this bug applied (`tests.test_3_invoices.TestInvoices.test_invoice_amounts`):

```
AssertionError: {'t-a[23 chars] '2.42', 't-cove': '0.28', 't-dune': '1.50', '[101 chars].25'} != {'t-a[23 chars] '2.43', 't-cove': '0.28', 't-dune': '1.50', '[101 chars].25'}
  {'t-acme': '0.32',
-  't-bolt': '2.42',
?                ^

+  't-bolt': '2.43',
?                ^

   't-cove': '0.28',
   't-dune': '1.50',
   't-echo': '0.00',
   't-fern': '0.56',
-  't-gale': '2.92',
?                 ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `meterbill/usage.py` → `billable`: It looks like it should exclude 4xx responses as well, but README rule 5 bills client errors and only drops 5xx, so `status < 500` is exactly the rule. tally() only calls it for allowed requests.
