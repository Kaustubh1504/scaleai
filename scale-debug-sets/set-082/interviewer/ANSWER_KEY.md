# set-082 answer key: Gateway metering: sliding-window limits and tiered invoices

**Domain:** rate_limit_billing  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_ingest.TestIngest.test_skipped_rows` | B1 Unparseable units swallowed as 0 |
| `test_1_ingest.TestIngest.test_same_instant_keeps_log_order` | B2 Same-instant requests re-ordered by id |
| `test_2_limits.TestRateLimits.test_rejected_requests` | B3 Window treated as closed at t − W |
| `test_2_limits.TestRateLimits.test_retry_after_hints` | B4 Retry hint drops fractional seconds |
| `test_3_invoices.TestInvoices.test_subtotals` | B5 Partial blocks dropped |
| `test_3_invoices.TestInvoices.test_discounted_total` | B6 Half-cent discount rounded to even |

## Failing pattern with all bugs present

- `tests.test_1_ingest.TestIngest.test_same_instant_keeps_log_order`
- `tests.test_1_ingest.TestIngest.test_skipped_rows`
- `tests.test_2_limits.TestRateLimits.test_rejected_requests`
- `tests.test_2_limits.TestRateLimits.test_retry_after_hints`
- `tests.test_3_invoices.TestInvoices.test_discounted_total`
- `tests.test_3_invoices.TestInvoices.test_subtotals`

## Bugs (recommended order)

### B1: Unparseable units swallowed as 0

- **Type:** swallowed-exception
- **Symptom:** Test 1 test_skipped_rows: malformed is [] instead of ['gw1-0010', 'gw2-0012']; unknown_tenant is unchanged. Nothing else fails: the two halcyon rows are replayed as 0-unit calls with headroom to spare.
- **Location:** `meterbill/loader.py` → `parse_units`
- **Why it fails:** load_requests relies on parse_units raising ValueError to classify a row as malformed. Catching it inside the helper and returning 0 hides the error, so the blank and `1.5k` rows are replayed and billed as zero-unit calls instead of being skipped.
- **Failing test:** `test_1_ingest.TestIngest.test_skipped_rows`
- **Unblocks:** test_1 test_skipped_rows.

Fix:

```diff
 def parse_units(value):
-    try:
-        return int(value.strip())
-    except ValueError:
-        return 0
+    return int(value.strip())
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_skipped_rows`):

```
AssertionError: {'malformed': [], 'unknown_tenant': ['gw2-0008', 'gw2-0015']} != {'malformed': ['gw1-0010', 'gw2-0012'], 'unknown_tenant'[22 chars]15']}
+ {'malformed': ['gw1-0010', 'gw2-0012'],
- {'malformed': [], 'unknown_tenant': ['gw2-0008', 'gw2-0015']}
? -----------------

+  'unknown_tenant': ['gw2-0008', 'gw2-0015']}
```

### B2: Same-instant requests re-ordered by id

- **Type:** wrong-tie-break
- **Symptom:** Test 1 test_same_instant_keeps_log_order: garnet's timeline is ['gw1-0011', 'gw2-0011', 'gw1-0012', 'gw2-0010']; each same-second pair is swapped.
- **Location:** `meterbill/timeparse.py` → `chronological`
- **Why it fails:** The spec keeps log order for equal timestamps, which a stable sort on ts alone already does. Adding request_id to the key breaks the tie by id, and ids come from two gateway shards, so gw1-… jumps ahead of gw2-….
- **Failing test:** `test_1_ingest.TestIngest.test_same_instant_keeps_log_order`
- **Unblocks:** test_1 test_same_instant_keeps_log_order.

Fix:

```diff
-    return sorted(requests, key=lambda r: (r.ts, r.request_id))
+    return sorted(requests, key=lambda r: r.ts)
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_same_instant_keeps_log_order`):

```
AssertionError: Lists differ: ['gw1-0011', 'gw2-0011', 'gw1-0012', 'gw2-0010'] != ['gw2-0011', 'gw1-0011', 'gw2-0010', 'gw1-0012']

First differing element 0:
'gw1-0011'
'gw2-0011'

- ['gw1-0011', 'gw2-0011', 'gw1-0012', 'gw2-0010']
+ ['gw2-0011', 'gw1-0011', 'gw2-0010', 'gw1-0012']
```

### B3: Window treated as closed at t − W

- **Type:** time-window-boundary
- **Symptom:** Test 2 test_rejected_requests: an extra rejection, gw2-0004 (elm-labs at 12:00:10, exactly 10 s after its first accepted call).
- **Location:** `meterbill/limiter.py` → `SlidingWindow.offer`
- **Why it fails:** The window is (t − W, t]. A request exactly W seconds old sits on the excluded boundary and must be evicted; with `<` it stays, so elm-labs' 12:00:10 call sees a full window.
- **Failing test:** `test_2_limits.TestRateLimits.test_rejected_requests`
- **Unblocks:** test_2 test_rejected_requests.

Fix:

```diff
-        while self.accepted and self.accepted[0] < cutoff:
+        while self.accepted and self.accepted[0] <= cutoff:
```

Observed with only this bug applied (`tests.test_2_limits.TestRateLimits.test_rejected_requests`):

```
AssertionError: Lists differ: ['gw1-0005', 'gw2-0004', 'gw2-0005', 'gw2-0006'] != ['gw1-0005', 'gw2-0005', 'gw2-0006']

First differing element 1:
'gw2-0004'
'gw2-0005'

First list contains 1 additional elements.
First extra element 3:
'gw2-0006'

- ['gw1-0005', 'gw2-0004', 'gw2-0005', 'gw2-0006']
?              ------------

+ ['gw1-0005', 'gw2-0005', 'gw2-0006']
```

### B4: Retry hint drops fractional seconds

- **Type:** timedelta-seconds
- **Symptom:** Test 2 test_retry_after_hints: dunmore hints are {'gw2-0005': 2.0, 'gw2-0006': 1.0} instead of 1.75 / 0.75. elm-labs' 3.0 hint is unchanged.
- **Location:** `meterbill/limiter.py` → `SlidingWindow.offer`
- **Why it fails:** timedelta.seconds is only the whole-seconds component (no microseconds, no days). dunmore's timestamps have millisecond fractions, so elapsed is truncated and every hint comes out larger by the dropped fraction.
- **Failing test:** `test_2_limits.TestRateLimits.test_retry_after_hints`
- **Unblocks:** test_2 test_retry_after_hints.

Fix:

```diff
-        elapsed = (ts - self.accepted[0]).seconds
+        elapsed = (ts - self.accepted[0]).total_seconds()
```

Observed with only this bug applied (`tests.test_2_limits.TestRateLimits.test_retry_after_hints`):

```
AssertionError: {'gw2-0005': 2.0, 'gw2-0006': 1.0} != {'gw2-0005': 1.75, 'gw2-0006': 0.75}
- {'gw2-0005': 2.0, 'gw2-0006': 1.0}
?              ^ ^              ^ ^

+ {'gw2-0005': 1.75, 'gw2-0006': 0.75}
?              ^ ^^              ^ ^^
```

### B5: Partial blocks dropped

- **Type:** integer-division
- **Symptom:** Test 3 test_subtotals: borealis 2180 (expected 2220), cinder/2026-02 4925 (4950), cinder/2026-03 6240 (6258). acme, dunmore, garnet and halcyon are unchanged.
- **Location:** `meterbill/plans.py` → `blocks_for`
- **Why it fails:** Floor division throws away the partial block, but the spec bills a partial block as a whole one. The double negation is the integer ceiling. Tenants whose billable units are an exact multiple of 1,000 (acme) or zero are unaffected.
- **Failing test:** `test_3_invoices.TestInvoices.test_subtotals`
- **Unblocks:** test_3 test_subtotals.

Fix:

```diff
-    return billable // BLOCK_UNITS  # whole blocks
+    return -(-billable // BLOCK_UNITS)  # whole blocks
```

Observed with only this bug applied (`tests.test_3_invoices.TestInvoices.test_subtotals`):

```
AssertionError: {'acm[34 chars]3': 2180, 'cinder/2026-02': 4925, 'cinder/2026[80 chars]1900} != {'acm[34 chars]3': 2220, 'cinder/2026-02': 4950, 'cinder/2026[80 chars]1900}
  {'acme/2026-03': 5050,
-  'borealis/2026-03': 2180,
?                       ^^

+  'borealis/2026-03': 2220,
?                       ^^

-  'cinder/2026-02': 4925,
?                      -

+  'cinder/2026-02': 4950,
?        ...
```

### B6: Half-cent discount rounded to even

- **Type:** float-rounding
- **Symptom:** Test 3 test_discounted_total: 4292 != 4293 for acme/2026-03.
- **Location:** `meterbill/invoices.py` → `apply_discount`
- **Why it fails:** round() uses banker's rounding (half to even), also for Decimal. 5050 × 0.85 = 4292.5, which rounds to 4292 instead of the spec's half-up 4293.
- **Failing test:** `test_3_invoices.TestInvoices.test_discounted_total`
- **Unblocks:** test_3 test_discounted_total.

Fix:

```diff
# meterbill/invoices.py
-    return round(discounted)
+    return int(discounted.quantize(Decimal(1), rounding=ROUND_HALF_UP))

# meterbill/invoices.py
-from decimal import Decimal
+from decimal import ROUND_HALF_UP, Decimal
```

Observed with only this bug applied (`tests.test_3_invoices.TestInvoices.test_discounted_total`):

```
AssertionError: 4292 != 4293
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `meterbill/timeparse.py` → `parse_ts`: It looks like it might drop offsets or choke on the trailing Z, but it rewrites Z as +00:00, lets fromisoformat handle the ISO/space forms (including fractions and offsets), falls back to the month/day slash format, assumes UTC when there is no offset and converts to UTC. That is exactly what pushes cinder's 00:30+01:00 request into February.
- `meterbill/plans.py` → `tiered_cents`: The floor/ceiling bookkeeping looks fragile, but each tier charges the blocks between the previous tier's limit and min(blocks, its own limit), stops once the usage fits, and treats null as unbounded. 56 blocks on growth is 50 x 25 + 6 x 18 = 1358.
