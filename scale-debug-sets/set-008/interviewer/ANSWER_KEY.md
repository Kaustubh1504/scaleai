# set-008 answer key: Vendor roster ingestion with cross-file dedupe

**Domain:** data_ingestion_dedupe  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_records.TestRecords.test_lineage` | B1 BOM kept in the first header |
| `test_1_records.TestRecords.test_skills` | B2 Merged skills keep repeats |
| `test_2_cleaning.TestCleaning.test_notes` | B3 Defaults copied shallowly |
| `test_2_cleaning.TestCleaning.test_rates` | B4 Day rate floor-divided |
| `test_3_summary.TestSummary.test_rejected_by_reason` | B5 Reason lookup checks the base class first |
| `test_3_summary.TestSummary.test_countries` | B6 Country aliases looked up before upper-casing |

## Failing pattern with all bugs present

- `tests.test_1_records.TestRecords.test_lineage`
- `tests.test_1_records.TestRecords.test_skills`
- `tests.test_2_cleaning.TestCleaning.test_notes`
- `tests.test_2_cleaning.TestCleaning.test_rates`
- `tests.test_3_summary.TestSummary.test_countries`
- `tests.test_3_summary.TestSummary.test_rejected_by_reason`

## Bugs (recommended order)

### B1: BOM kept in the first header

- **Type:** csv-bom-encoding
- **Symptom:** Test 1 test_lineage: every vendor_a source loses its reference ('vendor_a:' instead of 'vendor_a:A-101', 'vendor_a:A-102', 'vendor_a:A-110').
- **Location:** `rosterload/readers.py` → `read_csv`
- **Why it fails:** vendor_a.csv starts with a UTF-8 BOM. Decoded as plain utf-8, the BOM stays glued to the first header, so the column is `\ufeffsource_ref` and `row.get('source_ref')` finds nothing for every vendor_a row. `.strip()` does not remove U+FEFF.
- **Failing test:** `test_1_records.TestRecords.test_lineage`
- **Unblocks:** test_1_records.TestRecords.test_lineage.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_1_records.TestRecords.test_lineage`):

```
AssertionError: {'ash[17 chars]or_a:', 'vendor_b:B-201'], 'ben@lab.io': ['ven[69 chars]a:']} != {'ash[17 chars]or_a:A-101', 'vendor_b:B-201'], 'ben@lab.io': [84 chars]10']}
- {'asha@lab.io': ['vendor_a:', 'vendor_b:B-201'],
+ {'asha@lab.io': ['vendor_a:A-101', 'vendor_b:B-201'],
?                            +++++

-  'ben@lab.io': ['vendor_a:', 'vendor_b:B-202', 'vendor_c:C-307'],
+  'ben@lab.io': ...
```

### B2: Merged skills keep repeats

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_skills: merged contributors repeat skills, e.g. asha ['python', 'python', 'spark', 'sql'] and ben ['nlp', 'nlp', 'nlp', 'python', 'sql']. kai (never merged) is fine.
- **Location:** `rosterload/dedupe.py` → `merge_duplicates`
- **Why it fails:** The set comprehension was turned into a generator, so the union keeps every copy of a skill that appears in more than one row. Records that were never merged are fine because parse_skills already dedupes each row.
- **Failing test:** `test_1_records.TestRecords.test_skills`
- **Unblocks:** test_1_records.TestRecords.test_skills.

Fix:

```diff
-        out["skills"] = sorted(s for rec in group for s in rec["skills"])
+        out["skills"] = sorted({s for rec in group for s in rec["skills"]})
```

Observed with only this bug applied (`tests.test_1_records.TestRecords.test_skills`):

```
AssertionError: {'ash[18 chars]n', 'python', 'spark', 'sql'], 'ben@lab.io': [[147 chars]: []} != {'ash[18 chars]n', 'spark', 'sql'], 'ben@lab.io': ['nlp', 'py[104 chars]: []}
- {'asha@lab.io': ['python', 'python', 'spark', 'sql'],
?                            ----------

+ {'asha@lab.io': ['python', 'spark', 'sql'],
-  'ben@lab.io': ['nlp', 'nlp', 'nlp', 'python', 'sql'],
?                       - ...
```

### B3: Defaults copied shallowly

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 2 test_notes: all 16 records have notes, and every record shows the same long list of name_from_email / rate_missing entries collected from every row.
- **Location:** `rosterload/normalize.py` → `build_record`
- **Why it fails:** `dict(DEFAULTS)` copies the outer dict only; every record's `notes` is the same list object as `DEFAULTS["notes"]`. Each `append` lands in that one list, so every record shows every note from every row.
- **Failing test:** `test_2_cleaning.TestCleaning.test_notes`
- **Unblocks:** test_2_cleaning.TestCleaning.test_notes.

Fix:

```diff
# rosterload/normalize.py
-    record = dict(DEFAULTS)
+    record = copy.deepcopy(DEFAULTS)

# rosterload/normalize.py
+import copy
```

Observed with only this bug applied (`tests.test_2_cleaning.TestCleaning.test_notes`):

```
AssertionError: {'asha@lab.io': ['name_from_email', 'rate_m[3065 chars]il']} != {'lena@lab.io': ['name_from_email'], 'raj@l[56 chars]il']}
Diff is 6070 characters long. Set self.maxDiff to None to see it.
```

### B4: Day rate floor-divided

- **Type:** integer-division
- **Symptom:** Test 2 test_rates: kai@lab.io has 19.0 instead of 19.5. Every other rate is right.
- **Location:** `rosterload/normalize.py` → `parse_rate`
- **Why it fails:** `//` is floor division even on floats: 156.0 // 8 is 19.0, not 19.5. Only kai's rate is written as a day rate.
- **Failing test:** `test_2_cleaning.TestCleaning.test_rates`
- **Unblocks:** test_2_cleaning.TestCleaning.test_rates.

Fix:

```diff
-        rate = float(text[: -len("/day")]) // 8
+        rate = float(text[: -len("/day")]) / 8
```

Observed with only this bug applied (`tests.test_2_cleaning.TestCleaning.test_rates`):

```
AssertionError: {'ash[153 chars]: 19.0, 'lena@lab.io': 21.0, 'pia@lab.io': 0.0[119 chars]21.0} != {'ash[153 chars]: 19.5, 'lena@lab.io': 21.0, 'pia@lab.io': 0.0[119 chars]21.0}
  {'asha@lab.io': 24.0,
   'ben@lab.io': 32.0,
   'chen@lab.io': 26.0,
   'femi@lab.io': 27.0,
   'gita@lab.io': 28.0,
   'ines@lab.io': 24.0,
   'jon@lab.io': 35.0,
-  'kai@lab.io': 19.0,
?                   ^

+  'kai@lab ...
```

### B5: Reason lookup checks the base class first

- **Type:** exception-order
- **Symptom:** Test 3 test_rejected_by_reason: {'invalid_value': 8} instead of {'invalid_value': 5, 'missing_field': 3}.
- **Location:** `rosterload/pipeline.py` → `ingest`
- **Why it fails:** MissingField is a subclass of RowError, which is a ValueError. The lookup takes the first class the exception is an instance of, so with ValueError first every missing-email row is labelled invalid_value. The rows are still rejected, which is why only the summary changes.
- **Failing test:** `test_3_summary.TestSummary.test_rejected_by_reason`
- **Unblocks:** test_3_summary.TestSummary.test_rejected_by_reason.

Fix:

```diff
-REASONS = [(ValueError, "invalid_value"), (MissingField, "missing_field")]
+REASONS = [(MissingField, "missing_field"), (ValueError, "invalid_value")]
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_rejected_by_reason`):

```
AssertionError: {'invalid_value': 8} != {'invalid_value': 5, 'missing_field': 3}
- {'invalid_value': 8}
+ {'invalid_value': 5, 'missing_field': 3}
```

### B6: Country aliases looked up before upper-casing

- **Type:** id-normalization
- **Symptom:** Test 3 test_countries: keys such as 'us', 'uk', 'india', 'United States', 'ca', 'se' appear next to US/GB/IN, and US drops to 3.
- **Location:** `rosterload/schema.py` → `norm_country`
- **Why it fails:** COUNTRY_ALIASES keys are upper-case. Without `.upper()`, mixed-case values such as `us`, `uk`, `india` and `United States` miss the alias table and are kept as written.
- **Failing test:** `test_3_summary.TestSummary.test_countries`
- **Unblocks:** test_3_summary.TestSummary.test_countries.

Fix:

```diff
-    code = str(raw or "").strip()
+    code = str(raw or "").strip().upper()
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_countries`):

```
AssertionError: {'GB': 1, 'IN': 2, 'UNKNOWN': 1, 'US': 3, '[70 chars]': 1} != {'CA': 1, 'GB': 4, 'IN': 3, 'SE': 1, 'UNKNOWN': 1, 'US': 6}
+ {'CA': 1, 'GB': 4, 'IN': 3, 'SE': 1, 'UNKNOWN': 1, 'US': 6}
- {'GB': 1,
-  'IN': 2,
-  'UNKNOWN': 1,
-  'US': 3,
-  'United States': 2,
-  'ca': 1,
-  'gb': 1,
-  'india': 1,
-  'se': 1,
-  'uk': 2,
-  'us': 1}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `rosterload/dedupe.py` → `newer`: The `>=` looks like it lets an older row win, but the tuple includes the read order, so it only matters on an exact tie, where README rule 13 says the later row wins (femi: vendor_b replaces vendor_a).
- `rosterload/normalize.py` → `parse_date`: It accepts exactly the three formats in README rule 4 and raises RowError (a ValueError) otherwise, so bad dates become invalid_value.
