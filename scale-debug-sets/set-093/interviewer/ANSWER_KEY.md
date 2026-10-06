# set-093 answer key: Price quote TTL cache: key, stored copies, log span

**Domain:** cache_ttl  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_responses.TestResponses.test_sku2_quotes` | B1 Cache key leaves out the currency |
| `test_1_responses.TestResponses.test_sku1_quotes` | B2 Cache stores the caller's dict, which the discount then mutates |
| `test_2_summary.TestSummary.test_traffic_span` | B3 Log span uses timedelta.seconds |

## Failing pattern with all bugs present

- `tests.test_1_responses.TestResponses.test_sku1_quotes`
- `tests.test_1_responses.TestResponses.test_sku2_quotes`
- `tests.test_2_summary.TestSummary.test_traffic_span`

## Bugs (recommended order)

### B1: Cache key leaves out the currency

- **Type:** cache-key-missing-param
- **Symptom:** Test 1 test_sku2_quotes: r04 (GBP) comes back ('hit', 40.0), the EUR price, and r05 turns into ('miss', 34.5). The summary's hit and miss totals are unchanged.
- **Location:** `quotecache/replay.py` → `request_key`
- **Why it fails:** Without the currency, the EUR and GBP quotes for SKU-2/EU share one entry. r04 (GBP) is served r03's cached EUR price, and because that entry is older, r05 then finds it stale and refetches. The hit and miss totals happen to stay the same.
- **Failing test:** `test_1_responses.TestResponses.test_sku2_quotes`
- **Unblocks:** test_sku2_quotes.

Fix:

```diff
-    return (req.endpoint, req.sku, req.region)
+    return (req.endpoint, req.sku, req.region, req.currency)
```

Observed with only this bug applied (`tests.test_1_responses.TestResponses.test_sku2_quotes`):

```
AssertionError: {'r03[23 chars]': ('hit', 40.0), 'r05': ('miss', 34.5), 'r19'[34 chars]3.2)} != {'r03[23 chars]': ('miss', 34.5), 'r05': ('hit', 34.5), 'r19'[34 chars]3.2)}
  {'r03': ('miss', 40.0),
-  'r04': ('hit', 40.0),
-  'r05': ('miss', 34.5),
?     ^

+  'r04': ('miss', 34.5),
?     ^

+  'r05': ('hit', 34.5),
   'r19': ('miss', 43.2),
   'r20': ('hit', 43.2)}
```

### B2: Cache stores the caller's dict, which the discount then mutates

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 1 test_sku1_quotes: r02 and r18 (birch and cobalt, no discount) are charged 90.0 instead of 100.0, the price acme paid on the miss just before.
- **Location:** `quotecache/cache.py` → `TTLCache.put`
- **Why it fails:** serve() applies the client discount by changing quote["price"] in place. Without a copy in put(), that is the same dict the cache holds, so acme's 10% discount is baked into the cached entry and the next client to hit it gets 90.0.
- **Failing test:** `test_1_responses.TestResponses.test_sku1_quotes`
- **Unblocks:** test_sku1_quotes.

Fix:

```diff
-        self._entries[key] = Entry(value, now)
+        self._entries[key] = Entry(dict(value), now)
```

Observed with only this bug applied (`tests.test_1_responses.TestResponses.test_sku1_quotes`):

```
AssertionError: {'r01[24 chars]: ('hit', 90.0), 'r17': ('miss', 90.0), 'r18': ('hit', 90.0)} != {'r01[24 chars]: ('hit', 100.0), 'r17': ('miss', 90.0), 'r18': ('hit', 100.0)}
  {'r01': ('miss', 90.0),
-  'r02': ('hit', 90.0),
?                 ^

+  'r02': ('hit', 100.0),
?                 ^^

   'r17': ('miss', 90.0),
-  'r18': ('hit', 90.0)}
?                 ^

+  'r18': ('hit', 100.0)}
?       ...
```

### B3: Log span uses timedelta.seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 2 test_traffic_span: (1.5, 17.33) instead of (25.5, 1.02). The 1-day part of the log span is lost.
- **Location:** `quotecache/reports.py` → `summarize`
- **Why it fails:** timedelta.seconds is only the seconds part (0-86399) and leaves out whole days. The log covers 1 day 1.5 hours, so the span reads as 1.5 h and the rate is about 17 times too high.
- **Failing test:** `test_2_summary.TestSummary.test_traffic_span`
- **Unblocks:** test_traffic_span.

Fix:

```diff
-    span_hours = (last - first).seconds / 3600
+    span_hours = (last - first).total_seconds() / 3600
```

Observed with only this bug applied (`tests.test_2_summary.TestSummary.test_traffic_span`):

```
AssertionError: Tuples differ: (1.5, 17.33) != (25.5, 1.02)

First differing element 0:
1.5
25.5

- (1.5, 17.33)
+ (25.5, 1.02)
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `quotecache/cache.py` → `get`: `age < ttl` looks like it should be `<=`, but the spec says an entry is stale at exactly the TTL (r10, at exactly 3600 s, must miss). It uses total_seconds(), so day-old entries are seen as stale, and it returns a copy.
- `quotecache/loader.py` → `parse_ts`: The `/ 1000` looks like a ms-vs-s slip, but the numeric timestamps really are milliseconds and fromtimestamp takes seconds. It converts in UTC and drops the tzinfo so the values compare with the naive UTC strings.
