# set-056 answer key: Supplier catalog merge: BOM feeds, rejects, latest-wins dedupe

**Domain:** data_ingestion_dedupe  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_ingest.TestIngest.test_accepted_per_source`
- `tests.test_1_ingest.TestIngest.test_rejects`
- `tests.test_2_catalog.TestCatalog.test_catalog_records`
- `tests.test_2_catalog.TestCatalog.test_catalog_skus`
- `tests.test_3_summary.TestSummary.test_categories`
- `tests.test_3_summary.TestSummary.test_counts`

## Bugs (recommended order)

### B1: Feed opened as plain utf-8, BOM kept in the first header

- **Type:** csv-bom-encoding
- **Symptom:** All three files fail. Test 1: accepted shows supplier_a 0, and rejects list every supplier_a line (2-15) as missing_sku. Test 2: DR-200, EL-900 and PT-310 are missing and HM-100/LT-400 come from supplier_b. Test 3: counts become (1, 0, {missing_sku: 14, ...}).
- **Location:** `skufeed/readers.py` → `read_feed`
- **Why it fails:** supplier_a.csv starts with a byte-order mark. Read as plain utf-8, the first header becomes '\ufeffsku'; strip() does not remove U+FEFF, so row.get('sku') is empty and every supplier_a row is rejected as missing_sku.
- **Unblocks:** Most of Tests 1-3; exposes B2.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_accepted_per_source`):

```
AssertionError: {'supplier_a': 0, 'supplier_b': 10} != {'supplier_a': 8, 'supplier_b': 10}
- {'supplier_a': 0, 'supplier_b': 10}
?                ^

+ {'supplier_a': 8, 'supplier_b': 10}
?                ^
```

### B2: Non-numeric qty silently becomes 0

- **Type:** swallowed-exception
- **Symptom:** Only visible after B1 is fixed. Test 1: supplier_a accepted is 9 and the reject ('supplier_a', 8, 'bad_qty') is missing. Test 2: FS-600 appears in the catalog. Test 3: a 'fasteners' category appears (avg_price 9.49, units 0) and bad_qty drops to 1.
- **Location:** `skufeed/utils.py` → `parse_qty`
- **Why it fails:** The ValueError from int('twelve') is caught and turned into qty 0 instead of a bad_qty reject, so FS-600 is accepted and listed with zero stock.
- **Unblocks:** Test 1 rejects (supplier_a line 8), the Test 2 catalog and the Test 3 fasteners category.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-        return 0
+        raise RowError("bad_qty") from None
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_accepted_per_source`):

```
AssertionError: {'supplier_a': 9, 'supplier_b': 10} != {'supplier_a': 8, 'supplier_b': 10}
- {'supplier_a': 9, 'supplier_b': 10}
?                ^

+ {'supplier_a': 8, 'supplier_b': 10}
?                ^
```

### B3: Equal timestamps keep the earlier record

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_catalog_records: LT-400 comes from supplier_a (title 'LED shop light', 4500 cents, qty 8) instead of supplier_b. Test 3: lighting shows avg_price 30.15, stock_value 360.0, units 8. Test 1 passes.
- **Location:** `skufeed/dedupe.py` → `latest_by_sku`
- **Why it fails:** LT-400 has the same updated_at in both feeds (2026-04-03 vs 04/03/2026). The spec says the later read wins ties, but `>` keeps the first one seen, so supplier_a's title, price and qty are used.
- **Unblocks:** Test 2 LT-400 record and the Test 3 lighting row.

Fix:

```diff
-        if current is None or rec.updated_at > current.updated_at:
+        if current is None or rec.updated_at >= current.updated_at:
```

Observed with only this bug applied (`tests.test_2_catalog.TestCatalog.test_catalog_records`):

```
AssertionError: {'CB-[854 chars]light', 'category': 'lighting', 'price_cents':[502 chars]_b'}} != {'CB-[854 chars]light 4ft', 'category': 'lighting', 'price_cen[507 chars]_b'}}
  {'CB-120': {'category': 'electrical',
              'price_cents': 480,
              'qty': 60,
              'source': 'supplier_b',
              'title': 'Cable ties 100pk'},
   'DR-200': {'category': 'tools',
        ...
```

### B4: Zero price rejected as bad_price

- **Type:** falsy-zero
- **Symptom:** Test 1: supplier_b accepted is 9 and ('supplier_b', 5, 'bad_price') appears in rejects. Test 2: PR-050 is missing from the catalog. Test 3: safety has 1 SKU (avg_price 18.6) and bad_price is 3.
- **Location:** `skufeed/validate.py` → `build_record`
- **Why it fails:** `not price` is true for 0 cents as well as None, so the 0.00 promo gloves (PR-050) are rejected although the spec says 0.00 is a valid price.
- **Unblocks:** Test 1 rejects/accepted counts, PR-050 in Test 2, the safety row in Test 3.

Fix:

```diff
-    if not price:
+    if price is None:
         raise RowError("bad_price")
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_accepted_per_source`):

```
AssertionError: {'supplier_a': 8, 'supplier_b': 9} != {'supplier_a': 8, 'supplier_b': 10}
- {'supplier_a': 8, 'supplier_b': 9}
?                                 ^

+ {'supplier_a': 8, 'supplier_b': 10}
?                                 ^^
```

### B5: Category stats include discontinued SKUs

- **Type:** counting-wrong-subset
- **Symptom:** Test 3 test_categories only: garden shows skus 3, units 25, avg_price 21.53, stock_value 585.6, and paint also gains a SKU. Tests 1 and 2 pass.
- **Location:** `skufeed/reports.py` → `summarize`
- **Why it fails:** Grouping over every winner pulls in the discontinued GD-701 and PT-311, so garden and paint get extra SKUs and different averages and values. The spec computes category stats over the catalog only.
- **Unblocks:** Test 3 categories.
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-    for rec in winners.values():
+    for rec in catalog:
         groups[rec.category].append(rec)
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_categories`):

```
AssertionError: {'ele[90 chars]us': 3, 'units': 25, 'avg_price': 21.53, 'stoc[323 chars].88}} != {'ele[90 chars]us': 2, 'units': 16, 'avg_price': 21.6, 'stock[322 chars].88}}
  {'electrical': {'avg_price': 8.4, 'skus': 2, 'stock_value': 288.0, 'units': 60},
-  'garden': {'avg_price': 21.53, 'skus': 3, 'stock_value': 585.6, 'units': 25},
?                             ^^          ^                 ^ ...
```

### B6: Average price floored to whole cents

- **Type:** integer-division
- **Symptom:** Test 3 test_categories only: tools avg_price is 429.99 instead of 430.0. Every other category matches.
- **Location:** `skufeed/reports.py` → `summarize`
- **Why it fails:** Floor division truncates the mean in cents before rounding: tools is 128999 / 3 = 42999.67 cents, which should round to 430.00 but floors to 429.99.
- **Unblocks:** Test 3 categories (tools avg_price).
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-            "avg_price": round(sum(prices) // len(prices) / 100, 2),
+            "avg_price": round(sum(prices) / len(prices) / 100, 2),
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_categories`):

```
AssertionError: {'ele[401 chars]: 3, 'units': 37, 'avg_price': 429.99, 'stock_value': 4398.88}} != {'ele[401 chars]: 3, 'units': 37, 'avg_price': 430.0, 'stock_value': 4398.88}}
  {'electrical': {'avg_price': 8.4, 'skus': 2, 'stock_value': 288.0, 'units': 60},
   'garden': {'avg_price': 21.6, 'skus': 2, 'stock_value': 393.0, 'units': 16},
   'lighting': {'avg_price': 29.65, 'skus': 2, 'stock_value ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `skufeed/utils.py` → `parse_price`: Money through float looks risky, but round(float(text) * 100) is exact for two-decimal prices (19.99 * 100 = 1998.999... rounds to 1999). Returning None on blank or non-numeric text is what lets build_record raise bad_price, and None is distinct from a legitimate 0.
