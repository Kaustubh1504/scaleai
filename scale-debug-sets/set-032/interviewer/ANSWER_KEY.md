# set-032 answer key: Multi-vendor label feed: validate, merge, summarise

**Domain:** data_ingestion_dedupe  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_loading.TestLoading.test_rejections` | B1 Zero duration treated as missing |
| `test_2_records.TestRecords.test_same_time_submissions` | B2 Equal-time tie goes to the least trusted vendor |
| `test_2_records.TestRecords.test_merged_tags` | B3 Merged tags not de-duplicated |
| `test_3_summary.TestSummary.test_label_counts` | B4 Vendor label maps share one dict |
| `test_3_summary.TestSummary.test_tag_counts` | B5 Removing tags from the list being iterated |
| `test_3_summary.TestSummary.test_by_batch` | B6 BOM kept in the first CSV header |

## Failing pattern with all bugs present

- `tests.test_1_loading.TestLoading.test_rejections`
- `tests.test_2_records.TestRecords.test_merged_tags`
- `tests.test_2_records.TestRecords.test_same_time_submissions`
- `tests.test_3_summary.TestSummary.test_by_batch`
- `tests.test_3_summary.TestSummary.test_label_counts`
- `tests.test_3_summary.TestSummary.test_tag_counts`

## Bugs (recommended order)

### B1: Zero duration treated as missing

- **Type:** falsy-zero
- **Symptom:** Test 1 test_rejections: an extra entry acme:3 -> [missing_duration] (T003 from acme has duration 0). Records are unchanged because cortex wins T003 anyway.
- **Location:** `vendorfeed/validate.py` → `problems_for`
- **Why it fails:** `not rec.duration_s` is True for 0 as well as None, so a real zero-second duration is rejected. The README says 0 is a real value.
- **Failing test:** `test_1_loading.TestLoading.test_rejections`
- **Unblocks:** test_rejections.

Fix:

```diff
-    if not rec.duration_s:
+    if rec.duration_s is None:
         problems.append("missing_duration")
```

Observed with only this bug applied (`tests.test_1_loading.TestLoading.test_rejections`):

```
AssertionError: {'acme:3': ['missing_duration'], 'acme:4': ['bad[309 chars]mp']} != {'acme:4': ['bad_email'], 'acme:7': ['missing_ta[277 chars]mp']}
  {'acme:11': ['bad_timestamp'],
   'acme:12': ['negative_duration'],
   'acme:14': ['bad_email', 'bad_timestamp'],
-  'acme:3': ['missing_duration'],
   'acme:4': ['bad_email'],
   'acme:7': ['missing_task_id'],
   'acme:8': ['missing_duration'],
    ...
```

### B2: Equal-time tie goes to the least trusted vendor

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_same_time_submissions: T008 goes to brightlabel (k.osei) and T015 to cortex (s.ito). They should be acme and brightlabel.
- **Location:** `vendorfeed/dedupe.py` → `rank`
- **Why it fails:** merge() takes max() of rank, so the tie-break term must grow as trust grows. Priority 1 is the most trusted, so it has to be negated; without the minus the largest priority number (least trusted) wins.
- **Failing test:** `test_2_records.TestRecords.test_same_time_submissions`
- **Unblocks:** test_same_time_submissions.

Fix:

```diff
-    return (rec.submitted, rec.priority)
+    return (rec.submitted, -rec.priority)
```

Observed with only this bug applied (`tests.test_2_records.TestRecords.test_same_time_submissions`):

```
AssertionError: {'T008': ('brightlabel', 'k.osei@brightlabel.com'), [33 chars]ai')} != {'T008': ('acme', 'j.ruiz@acme.io'), 'T015': ('brigh[30 chars]om')}
+ {'T008': ('acme', 'j.ruiz@acme.io'),
- {'T008': ('brightlabel', 'k.osei@brightlabel.com'),
? ^   ^^                    ^ ^^^                   ^

+  'T015': ('brightlabel', 'r.diaz@brightlabel.com')}
? ^   ^^                    ^ ^ ++          ...
```

### B3: Merged tags not de-duplicated

- **Type:** missing-dedupe
- **Symptom:** Test 2 test_merged_tags: merged records repeat tags, e.g. T001 [sentiment, sentiment, short, short], T002 [sarcasm, sentiment, sentiment].
- **Location:** `vendorfeed/dedupe.py` → `merge`
- **Why it fails:** Without the set, a tag that appears on several copies is repeated in the final record. The README says the tags are the sorted distinct tags.
- **Failing test:** `test_2_records.TestRecords.test_merged_tags`
- **Unblocks:** test_merged_tags.

Fix:

```diff
-    tags = sorted(tag for rec in copies for tag in rec.tags)
+    tags = sorted({tag for rec in copies for tag in rec.tags})
```

Observed with only this bug applied (`tests.test_2_records.TestRecords.test_merged_tags`):

```
AssertionError: {'T00[15 chars]', 'sentiment', 'short', 'short'], 'T002': ['s[243 chars]rt']} != {'T00[15 chars]', 'short'], 'T002': ['sarcasm', 'sentiment'],[157 chars]rt']}
- {'T001': ['sentiment', 'sentiment', 'short', 'short'],
+ {'T001': ['sentiment', 'short'],
-  'T002': ['sarcasm', 'sentiment', 'sentiment'],
?                     -------------

+  'T002': ['sarcasm', 'sentiment'],
-  'T003' ...
```

### B4: Vendor label maps share one dict

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 3 test_label_counts: {negative: 7, neutral: 7, positive: 8}; the mixed: 1 entry is gone and neutral is one too high.
- **Location:** `vendorfeed/config.py` → `vendor_settings`
- **Why it fails:** A shallow copy shares the nested `label_map` dict, so each vendor's update() writes into the defaults and every vendor ends up using the union of all maps. brightlabel's `mixed → neutral` leaks into cortex.
- **Failing test:** `test_3_summary.TestSummary.test_label_counts`
- **Unblocks:** test_label_counts.

Fix:

```diff
-        settings = copy.copy(defaults)
+        settings = copy.deepcopy(defaults)
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_label_counts`):

```
AssertionError: {'negative': 7, 'neutral': 7, 'positive': 8} != {'mixed': 1, 'negative': 7, 'neutral': 6, 'positive': 8}
- {'negative': 7, 'neutral': 7, 'positive': 8}
?                            ^

+ {'mixed': 1, 'negative': 7, 'neutral': 6, 'positive': 8}
?  ++++++++++++                          ^
```

### B5: Removing tags from the list being iterated

- **Type:** mutate-while-iterating
- **Symptom:** Test 3 test_tag_counts: an extra tmp:review: 1 entry.
- **Location:** `vendorfeed/utils.py` → `split_tags`
- **Why it fails:** Removing an element shifts the rest left, so the loop skips the element after each removal. In 'tmp:qa;tmp:review;short' the second internal tag is never checked and survives.
- **Failing test:** `test_3_summary.TestSummary.test_tag_counts`
- **Unblocks:** test_tag_counts.

Fix:

```diff
-    for tag in tags:
+    for tag in list(tags):
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_tag_counts`):

```
AssertionError: {'long': 7, 'sarcasm': 5, 'sentiment': 7, 'short': 9, 'tmp:review': 1} != {'long': 7, 'sarcasm': 5, 'sentiment': 7, 'short': 9}
- {'long': 7, 'sarcasm': 5, 'sentiment': 7, 'short': 9, 'tmp:review': 1}
?                                                     -----------------

+ {'long': 7, 'sarcasm': 5, 'sentiment': 7, 'short': 9}
```

### B6: BOM kept in the first CSV header

- **Type:** csv-bom-encoding
- **Symptom:** Test 3 test_by_batch: {b1: 2, b4: 4, b5: 3, b6: 5, unbatched: 8}; b2 and b3 vanish and every acme winner lands in unbatched.
- **Location:** `vendorfeed/loader.py` → `read_rows`
- **Why it fails:** acme.csv starts with a byte order mark. Read as plain utf-8, the first header becomes '\ufeffbatch', so raw.get('batch') is None for every acme row and they all fall back to 'unbatched'.
- **Failing test:** `test_3_summary.TestSummary.test_by_batch`
- **Unblocks:** test_by_batch.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_by_batch`):

```
AssertionError: {'b1': 2, 'b4': 4, 'b5': 3, 'b6': 5, 'unbatched': 8} != {'b1': 3, 'b2': 3, 'b3': 1, 'b4': 4, 'b5': 3, 'b6': 5, 'unbatched': 3}
- {'b1': 2, 'b4': 4, 'b5': 3, 'b6': 5, 'unbatched': 8}
?                                                   ^

+ {'b1': 3, 'b2': 3, 'b3': 1, 'b4': 4, 'b5': 3, 'b6': 5, 'unbatched': 3}
?        +++++ ++++ +++++++++                                         ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `vendorfeed/utils.py` → `parse_timestamp`: The `%d.%m.%Y` format looks like it swaps day and month compared with the slash format, but the README says dotted dates are day.month.year and slash dates are month/day/year. Returning None for unparseable values is intentional: validation turns None into bad_timestamp.
