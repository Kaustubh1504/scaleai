# set-056 interviewer notes

**Scenario:** Two supplier CSV feeds (one exported with a UTF-8 BOM) are validated row by row with ordered reject codes, merged to one record per SKU (latest updated_at wins, later read wins ties), and summarised per category. Test 3 is the stock summary.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Feed opened as plain utf-8, BOM kept in the first header

1. **Nudge:** Every supplier_a row is rejected as missing_sku, but the file clearly has SKUs. What is different about that file?
2. **Area:** Print the header keys read_feed produces for supplier_a.csv.
3. **Exact:** Open the feed with encoding="utf-8-sig".

### B2: Non-numeric qty silently becomes 0

1. **Nudge:** Which SKU appears in the catalog that the spec says should have been rejected?
2. **Area:** Look at what happens when qty is not a whole number.
3. **Exact:** parse_qty's except ValueError should raise RowError("bad_qty"), not return 0.

### B3: Equal timestamps keep the earlier record

1. **Nudge:** Compare LT-400 in the catalog with its two rows in the feeds. Which one should win?
2. **Area:** Look at how latest_by_sku handles two records with the same updated_at.
3. **Exact:** Use `>=` so a later record replaces an equal-timestamp one.

### B4: Zero price rejected as bad_price

1. **Nudge:** PR-050 shows up as a bad_price reject. What is its price?
2. **Area:** Look at how build_record decides the price is unusable.
3. **Exact:** Check `price is None`, not `not price`.

### B5: Category stats include discontinued SKUs

1. **Nudge:** garden lists 3 SKUs in the summary but only 2 in the catalog. Where does the third come from?
2. **Area:** Look at which collection summarize groups by category.
3. **Exact:** Group over `catalog`, not `winners.values()`.

### B6: Average price floored to whole cents

1. **Nudge:** Only tools has an avg_price that differs, by one cent. What is special about its prices?
2. **Area:** Look at how avg_price is computed.
3. **Exact:** Use `/` instead of `//` before rounding.

## "Why did that fix work?" probes

**B1**
- Why didn't strip() in _normalise remove the BOM?
- Why was supplier_b unaffected?

**B2**
- Why was this invisible until the encoding fix?
- Why is a blank qty allowed to become 0 when 'twelve' is not?

**B3**
- The two LT-400 dates are written in different formats. Why do they still compare equal?
- Which data order would make `>` and `>=` give the same answer?

**B4**
- Why does parse_price return None for blank text instead of 0?
- What else in this codebase could legitimately be 0 and get caught by the same pattern?

**B5**
- Why does Test 2 never see this?
- Which other summary field legitimately uses winners rather than the catalog?

**B6**
- Why are the other categories unaffected?
- Would `round(sum(prices) / len(prices)) / 100` match the spec here? When could it differ?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `skufeed/utils.py` → `parse_price`: Money through float looks risky, but round(float(text) * 100) is exact for two-decimal prices (19.99 * 100 = 1998.999... rounds to 1999). Returning None on blank or non-numeric text is what lets build_record raise bad_price, and None is distinct from a legitimate 0.
