# set-080 answer key: Multi-vendor contributor roster: validate, merge, export

**Domain:** data_ingestion_dedupe  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_ingest.TestIngest.test_rejected_rows`
- `tests.test_1_ingest.TestIngest.test_source_counts`
- `tests.test_2_roster.TestRoster.test_duplicates`
- `tests.test_2_roster.TestRoster.test_members`
- `tests.test_2_roster.TestRoster.test_records`
- `tests.test_3_export.TestExport.test_countries`
- `tests.test_3_export.TestExport.test_export_timestamps`
- `tests.test_3_export.TestExport.test_skill_counts`

## Bugs (recommended order)

### B1: CSV opened without BOM handling

- **Type:** csv-bom-encoding
- **Symptom:** Every test file fails. Test 1: vendor_a shows accepted 0 / rejected 11 / inactive 0, and every vendor_a row is rejected as 'missing email'. Test 2: duplicates is 3 instead of 6, dev/gus/noa are missing, ana has hours 28 and skills ['spark', 'sql'] (vendor_b only). Test 3: python count 4, IL and SE missing, ana's timestamp is 2026-02-20T10:00:00.
- **Location:** `rosterflow/readers.py` → `read_csv_source`
- **Why it fails:** vendor_a.csv starts with a UTF-8 BOM. Read as plain utf-8, the first header becomes '\ufeffemail', so row.get('email') is None for every vendor_a row and all 11 are rejected as `missing email`. vendor_b has no BOM and is unaffected.
- **Unblocks:** All vendor_a contributors (ana's merge, dev, gus, noa, kim's tie). It also exposes B2.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_rejected_rows`):

```
AssertionError: Lists differ: [('vendor_a', 1, 'missing email'), ('vendor_a', 2, 'mis[492 chars]te')] != [('vendor_a', 9, 'missing email'), ('vendor_a', 10, 'in[220 chars]te')]

First differing element 0:
('vendor_a', 1, 'missing email')
('vendor_a', 9, 'missing email')

First list contains 8 additional elements.
First extra element 8:
('vendor_a', 9, 'missing email')

- [('vendor_a', 1, 'missing  ...
```

### B2: String 'FALSE' treated as active

- **Type:** bool-from-string
- **Symptom:** Masked by B1 (vendor_a rows are all rejected). Once B1 is fixed: Test 1 shows vendor_a accepted 8 / inactive 0, Test 2 has extra ben@x.io and leo@x.io in the roster, and Test 3 gains GB, NG, 'java' and a third 'spark'.
- **Location:** `rosterflow/normalize.py` → `parse_active`
- **Why it fails:** bool() of any non-empty string is True, so vendor_a's 'FALSE'/'false' rows count as active. Only vendor_a uses string flags (vendor_c uses JSON booleans and vendor_b has no column), so the problem stays hidden while vendor_a is fully rejected.
- **Unblocks:** vendor_a inactive count and the roster membership (ben, leo).
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
+    if isinstance(value, str):
+        return value.strip().lower() in TRUTHY
     return bool(value)
```

Observed with only this bug applied (`tests.test_1_ingest.TestIngest.test_source_counts`):

```
AssertionError: {'ven[28 chars]ed': 8, 'rejected': 3, 'inactive': 0}, 'vendor[129 chars]: 1}} != {'ven[28 chars]ed': 6, 'rejected': 3, 'inactive': 2}, 'vendor[129 chars]: 1}}
- {'vendor_a': {'accepted': 8, 'inactive': 0, 'rejected': 3, 'rows': 11},
?                           ^              ^

+ {'vendor_a': {'accepted': 6, 'inactive': 2, 'rejected': 3, 'rows': 11},
?                           ^   ...
```

### B3: Merged skills not de-duplicated

- **Type:** missing-dedupe
- **Symptom:** Test 2 test_records: merged people repeat skills (ana `['python', 'spark', 'sql', 'sql']`, gus `['python', 'python']`, cara/mia/raj likewise). Test 3 test_skill_counts: python 11, sql 6, labeling 2.
- **Location:** `rosterflow/dedupe.py` → `merge`
- **Why it fails:** Without the set, the skills from every duplicate row are simply concatenated, so people with more than one row get repeated skills (gus: python, python; ana: sql, sql). skill_counts counts list entries, so it is inflated too (python 11 instead of 8).
- **Unblocks:** Test 2 records for merged contributors, and the Test 3 skill counts.

Fix:

```diff
-            skills=sorted(s for r in group for s in r.skills),
+            skills=sorted({s for r in group for s in r.skills}),
```

Observed with only this bug applied (`tests.test_2_roster.TestRoster.test_records`):

```
AssertionError: {'ana[89 chars]'sql', 'sql'], 'sources': ['vendor_a', 'vendor[1692 chars]c']}} != {'ana[89 chars]'sql'], 'sources': ['vendor_a', 'vendor_b']}, [1636 chars]c']}}
  {'ana@x.io': {'country': 'ES',
                'hours': 30,
                'name': 'Ana Ruiz',
-               'skills': ['python', 'spark', 'sql', 'sql'],
?                                             -------

+         ...
```

### B4: Blank skill entries kept after split

- **Type:** empty-split
- **Symptom:** Test 2 test_records: dev `['', 'python']`, fay `['']`, uma `['', 'ml', 'python']`. Test 3 test_skill_counts gains a `'': 3` entry.
- **Location:** `rosterflow/normalize.py` → `parse_skills`
- **Why it fails:** "".split(";") is [""] and "python;".split(";") ends with "", so a blank cell or a trailing separator produces an empty-string skill. The spec drops empty entries.
- **Unblocks:** Test 2 records (fay, dev, uma) and the '' key in Test 3 skill_counts.

Fix:

```diff
-    return [text(s).lower() for s in items]
+    return [text(s).lower() for s in items if text(s)]
```

Observed with only this bug applied (`tests.test_2_roster.TestRoster.test_records`):

```
AssertionError: {'ana[339 chars]': ['', 'python'], 'sources': ['vendor_a']}, '[1396 chars]c']}} != {'ana[339 chars]': ['python'], 'sources': ['vendor_a']}, 'eli@[1386 chars]c']}}
  {'ana@x.io': {'country': 'ES',
                'hours': 30,
                'name': 'Ana Ruiz',
                'skills': ['python', 'spark', 'sql'],
                'sources': ['vendor_a', 'vendor_b']},
   'cara@x.io': ...
```

### B5: Timestamp ties go to the least trusted source

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_records: cara becomes `{'name': 'Cara D.', 'country': 'US', 'hours': 35}` (vendor_c) instead of Cara Diaz / MX / 40, and kim gets vendor_a's hours 15 instead of 18. Test 3 test_countries: MX missing, US 2.
- **Location:** `rosterflow/dedupe.py` → `pick_winner`
- **Why it fails:** Priority 1 is the most trusted, so on an updated_at tie the lower number has to win. max() over (updated_at, priority) picks the higher number, so cara takes vendor_c's name/country/hours and kim takes vendor_a's hours.
- **Unblocks:** Test 2 records for cara (and kim once B1 is fixed), and the Test 3 country counts.

Fix:

```diff
-    return max(group, key=lambda r: (r.updated_at, r.priority))
+    return max(group, key=lambda r: (r.updated_at, -r.priority))
```

Observed with only this bug applied (`tests.test_2_roster.TestRoster.test_records`):

```
AssertionError: {'ana[159 chars]ara D.', 'country': 'US', 'hours': 35, 'skills[1564 chars]c']}} != {'ana[159 chars]ara Diaz', 'country': 'MX', 'hours': 40, 'skil[1566 chars]c']}}
  {'ana@x.io': {'country': 'ES',
                'hours': 30,
                'name': 'Ana Ruiz',
                'skills': ['python', 'spark', 'sql'],
                'sources': ['vendor_a', 'vendor_b']},
-  'cara@x.io': ...
```

### B6: Export serialises datetimes with str()

- **Type:** json-serialization
- **Symptom:** Test 3 only, test_export_timestamps: every timestamp has a space instead of 'T' (`'2026-03-01 09:30:00'` vs `'2026-03-01T09:30:00'`).
- **Location:** `rosterflow/serialize.py` → `_encode`
- **Why it fails:** `str(datetime)` uses a space separator ('2026-03-01 09:30:00'), not the ISO-8601 'T' the spec requires. json.dumps hands every datetime to `_encode`, so every exported timestamp has the space.
- **Unblocks:** test_export_timestamps.
- **Masked:** only surfaces in test_3_export.

Fix:

```diff
-        return str(value)
+        return value.isoformat()
```

Observed with only this bug applied (`tests.test_3_export.TestExport.test_export_timestamps`):

```
AssertionError: {'ana[14 chars]03-01 09:30:00', 'cara@x.io': '2026-03-05 10:0[456 chars]:00'} != {'ana[14 chars]03-01T09:30:00', 'cara@x.io': '2026-03-05T10:0[456 chars]:00'}
- {'ana@x.io': '2026-03-01 09:30:00',
?                         ^

+ {'ana@x.io': '2026-03-01T09:30:00',
?                         ^

-  'cara@x.io': '2026-03-05 10:00:00',
?                          ^

+  'cara@x.io': '2026- ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `rosterflow/normalize.py` → `clean_email`: Stripping 'mailto:' looks like it might mangle addresses, but the README requires it, and only a leading prefix is removed. Lower-casing the whole address is also what the spec asks for.
- `rosterflow/normalize.py` → `parse_updated`: Returning None instead of raising looks like a swallowed error, but check_row turns None into the `unparseable date` rejection the README asks for. The four formats match the README exactly, including the bare date (midnight) and month/day/year.
