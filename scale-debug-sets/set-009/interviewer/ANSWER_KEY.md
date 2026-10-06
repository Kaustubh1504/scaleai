# set-009 answer key: NER span merger with inclusive-end exports

**Domain:** ner_spans  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_spans.TestSpans.test_kept_span_counts`
- `tests.test_1_spans.TestSpans.test_misaligned`
- `tests.test_1_spans.TestSpans.test_overlaps_resolved`
- `tests.test_2_entities.TestEntities.test_docs_with_entities`
- `tests.test_2_entities.TestEntities.test_entities`
- `tests.test_2_entities.TestEntities.test_label_counts`

## Bugs (recommended order)

### B1: Inclusive end not converted

- **Type:** span-offset-off-by-one
- **Symptom:** All 38 spans are misaligned. Test 1: kept is {} and test_overlaps_resolved raises KeyError: 'ann-c'. Test 2: no entities at all and label_counts is {}.
- **Location:** `spanmerge/loader.py` → `load_spans`
- **Why it fails:** The CSV's `end` is the last character (inclusive) but spans are half-open internally. Without `+ 1` every span covers one character too few, so `text[start:end]` never equals the quote and every span is misaligned.
- **Unblocks:** Both test files; exposes B2 and B3.

Fix:

```diff
-                end=end,
+                end=end + 1,
```

Observed with only this bug applied (`tests.test_1_spans.TestSpans.test_kept_span_counts`):

```
AssertionError: {} != {'ann-a': 14, 'ann-b': 11, 'ann-c': 9}
- {}
+ {'ann-a': 14, 'ann-b': 11, 'ann-c': 9}
```

### B2: List shrunk while looping over it

- **Type:** mutate-while-iterating
- **Symptom:** Only visible once B1 is fixed. Test 1: ann-c keeps 10 spans instead of 9, and on d10 keeps [[0, 18, 'ORG'], [10, 18, 'ORG']]. Test 2: Ericsson on d10 has 3 votes instead of 2.
- **Location:** `spanmerge/spans.py` → `resolve_overlaps`
- **Why it fails:** Removing an item from the list being iterated shifts the next item into the current index, so the loop skips it. In ann-c's d10 spans, 'Nokia' is removed and 'Ericsson', which also overlaps the longer span, is never examined.
- **Unblocks:** test_1_spans overlap and count tests, and Ericsson's votes in test_2.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-    for span in spans:
+    for span in list(spans):
```

Observed with only this bug applied (`tests.test_1_spans.TestSpans.test_kept_span_counts`):

```
AssertionError: {'ann-a': 14, 'ann-b': 11, 'ann-c': 10} != {'ann-a': 14, 'ann-b': 11, 'ann-c': 9}
- {'ann-a': 14, 'ann-b': 11, 'ann-c': 10}
?                                     ^^

+ {'ann-a': 14, 'ann-b': 11, 'ann-c': 9}
?                                     ^
```

### B3: Doc loop returns on the first unannotated doc

- **Type:** early-return
- **Symptom:** Only visible once B1 is fixed. Test 2: entities exist only for d01 and d02; d04, d05, d07, d08 and d10 are missing, and label_counts shrinks.
- **Location:** `spanmerge/consensus.py` → `build_entities`
- **Why it fails:** d03 has no annotations. `return` instead of `continue` stops the whole loop there, so no document after d03 is processed.
- **Unblocks:** test_2_entities.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
         if not spans:
-            return entities
+            continue
```

Observed with only this bug applied (`tests.test_2_entities.TestEntities.test_docs_with_entities`):

```
AssertionError: Lists differ: ['d01', 'd02'] != ['d01', 'd02', 'd04', 'd05', 'd07', 'd08', 'd10']

Second list contains 5 additional elements.
First extra element 2:
'd04'

- ['d01', 'd02']
+ ['d01', 'd02', 'd04', 'd05', 'd07', 'd08', 'd10']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `spanmerge/spans.py` → `overlaps`: Strict `<` looks as if it might miss touching spans, but with half-open offsets `[0, 5)` and `[5, 9)` share no character, and README rule 5 says touching spans do not overlap.
