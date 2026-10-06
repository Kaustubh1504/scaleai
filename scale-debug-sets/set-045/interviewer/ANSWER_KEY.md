# set-045 answer key: Price-quote TTL cache with per-model TTLs and tenant discounts

**Domain:** cache_ttl  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_quotes.TestQuotes.test_hits`
- `tests.test_1_quotes.TestQuotes.test_prices`
- `tests.test_2_summary.TestSummary.test_origin_calls`
- `tests.test_2_summary.TestSummary.test_stale_served`
- `tests.test_2_summary.TestSummary.test_tenants`

## Bugs (recommended order)

### B1: Cache key ignores region

- **Type:** cache-key-missing-param
- **Symptom:** Test 1: R03, R05, R14 and others become hits served the other region's price (R03 0.40 instead of 0.44, R05 1.98 instead of 1.8). Test 2: origin_calls 12 instead of 16, stale_served ['R03', 'R05', 'R08', 'R14', 'R16', 'R18', 'R23'], and every tenant's hits and spend change.
- **Location:** `cachekit/client.py` → `QuoteService.cache_key`
- **Why it fails:** Prices differ by region, but the key is the model alone, so an EU request is served whatever US entry is cached (and the other way round). Misses also refresh the shared entry at different times, which shifts every later expiry.
- **Unblocks:** Most of Test 1 and Test 2. It also exposes B2.

Fix:

```diff
-        return model
+        return (model, region)
```

Observed with only this bug applied (`tests.test_1_quotes.TestQuotes.test_hits`):

```
AssertionError: Lists differ: ['R02', 'R03', 'R05', 'R06', 'R08', 'R09', 'R14', 'R[41 chars]R25'] != ['R02', 'R06', 'R08', 'R09', 'R16', 'R17', 'R20', 'R[13 chars]R25']

First differing element 1:
'R03'
'R06'

First list contains 4 additional elements.
First extra element 10:
'R21'

+ ['R02', 'R06', 'R08', 'R09', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25']
- ['R02',
-  'R03',
-  'R05',
-  'R06',
-   ...
```

### B2: Entry still served at its exact expiry instant

- **Type:** time-window-boundary
- **Symptom:** Only visible after B1 is fixed. Test 1 test_hits: R10 shows up as a hit (its price is unchanged at 1.6). Test 2: origin_calls 15 instead of 16, initech hits 4 instead of 3.
- **Location:** `cachekit/store.py` → `TTLCache.get`
- **Why it fails:** The spec says an entry stored at t with TTL s has expired at t + s. With `<=`, R10 (10:04:00, exactly 120 s after R05 stored m-large/us) is a hit instead of a miss.
- **Unblocks:** Test 1 hits, Test 2 origin_calls and initech's hit count.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-        if now <= entry.expires_at:
+        if now < entry.expires_at:
```

Observed with only this bug applied (`tests.test_1_quotes.TestQuotes.test_hits`):

```
AssertionError: Lists differ: ['R02', 'R06', 'R08', 'R09', 'R10', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25'] != ['R02', 'R06', 'R08', 'R09', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25']

First differing element 4:
'R10'
'R16'

First list contains 1 additional elements.
First extra element 10:
'R25'

- ['R02', 'R06', 'R08', 'R09', 'R10', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25']
?                       ...
```

### B3: TTL of 0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 1 test_hits: R13 (m-embed) is a hit. Test 2: origin_calls 15 instead of 16, acme hits 4 instead of 3. No price changes.
- **Location:** `cachekit/client.py` → `QuoteService.ttl_for`
- **Why it fails:** `x or default` treats a real TTL of 0 as missing, so m-embed (which must never be cached) gets the 60 s default. R13, five seconds after R12, becomes a cache hit.
- **Unblocks:** Test 1 hits, Test 2 origin_calls and acme's hit count.

Fix:

```diff
-        return self.ttls.get(model) or self.default_ttl
+        return self.ttls.get(model, self.default_ttl)
```

Observed with only this bug applied (`tests.test_1_quotes.TestQuotes.test_hits`):

```
AssertionError: Lists differ: ['R02', 'R06', 'R08', 'R09', 'R13', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25'] != ['R02', 'R06', 'R08', 'R09', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25']

First differing element 4:
'R13'
'R16'

First list contains 1 additional elements.
First extra element 10:
'R25'

- ['R02', 'R06', 'R08', 'R09', 'R13', 'R16', 'R17', 'R20', 'R21', 'R24', 'R25']
?                       ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `cachekit/origin.py` → `price_at`: `start <= at` is right: a price takes effect at its effective_from instant, so a request at exactly 10:03:00 sees the new price. `start >= best[0]` keeps the latest effective row, and on a tie the later file row wins, which never happens in this data.
