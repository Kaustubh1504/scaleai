# set-081 answer key: Entity span audit: trim, snap, score

**Domain:** ner_spans  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_spans.TestSpanNormalization.test_exported_spans` | B1 Snap covers the token that starts at the span end |
| `test_2_scores.TestAgreementReport.test_annotator_scores` | B2 Non-gold spans scored as false positives |
| `test_2_scores.TestAgreementReport.test_label_confusions` | B3 Confusion ties left in insertion order |

## Failing pattern with all bugs present

- `tests.test_1_spans.TestSpanNormalization.test_exported_spans`
- `tests.test_2_scores.TestAgreementReport.test_annotator_scores`
- `tests.test_2_scores.TestAgreementReport.test_label_confusions`

## Bugs (recommended order)

### B1: Snap covers the token that starts at the span end

- **Type:** span-offset-off-by-one
- **Symptom:** Test 1 test_exported_spans: four spans grow by one character to swallow the following punctuation: 'Redwood Media,' (25, 39), 'Dublin.' (52, 59), 'Global Freight Inc.' (0, 19) and 'Milan.' (53, 59). Spans followed by a space are unchanged.
- **Location:** `spanalign/tokens.py` → `snap`
- **Why it fails:** With end-exclusive offsets, a token that starts exactly at `end` shares no character with the span. `<=` pulls in a punctuation mark that directly follows the entity ("Redwood Media,", "Dublin."), widening the span by one. Words followed by a space are unaffected, which is why only some spans move.
- **Failing test:** `test_1_spans.TestSpanNormalization.test_exported_spans`
- **Unblocks:** test_1 test_exported_spans.

Fix:

```diff
-    covered = [t for t in tokens if t.start <= end and t.end > start]
+    covered = [t for t in tokens if t.start < end and t.end > start]
```

Observed with only this bug applied (`tests.test_1_spans.TestSpanNormalization.test_exported_spans`):

```
AssertionError: {'D07[49 chars]25, 39, 'ORG', 'ann-a', 'Redwood Media,'], [52[325 chars]y']]} != {'D07[49 chars]25, 38, 'ORG', 'ann-a', 'Redwood Media'], [52,[321 chars]y']]}
  {'D07': [[0, 12, 'PERSON', 'ann-a', "Liam O'Brien"],
-          [25, 39, 'ORG', 'ann-a', 'Redwood Media,'],
?                ^                                -

+          [25, 38, 'ORG', 'ann-a', 'Redwood Media'],
?        ...
```

### B2: Non-gold spans scored as false positives

- **Type:** counting-wrong-subset
- **Symptom:** Test 2 test_annotator_scores: ann-a shows fp 4 / precision 0.636 / f1 0.7 (expected fp 1, 0.875, 0.824), ann-b fp 7 / precision 0.364 / f1 0.32, and an extra ann-d row with tp 0, fp 3 and all metrics 0.0. tp, fn and recall are unchanged.
- **Location:** `spanalign/scoring.py` → `score_annotators`
- **Why it fails:** `scored` is the gold-document subset, but the loop walks every accepted span. Spans on documents with no gold become false positives, and ann-d, who only annotated non-gold documents, gets a row with tp 0.
- **Failing test:** `test_2_scores.TestAgreementReport.test_annotator_scores`
- **Unblocks:** test_2 test_annotator_scores.

Fix:

```diff
-    for span in spans:
+    for span in scored:
         predicted[span.annotator].add(_key(span))
```

Observed with only this bug applied (`tests.test_2_scores.TestAgreementReport.test_annotator_scores`):

```
AssertionError: {'ann[16 chars]fp': 4, 'fn': 2, 'precision': 0.636, 'recall':[272 chars]0.0}} != {'ann[16 chars]fp': 1, 'fn': 2, 'precision': 0.875, 'recall':[191 chars]588}}
- {'ann-a': {'f1': 0.7,
?                    ^

+ {'ann-a': {'f1': 0.824,
?                    ^^^

             'fn': 2,
-            'fp': 4,
?                  ^

+            'fp': 1,
?                  ^

-            'p ...
```

### B3: Confusion ties left in insertion order

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_label_confusions: [['ORG', 'LOC', 2], ['LOC', 'ORG', 2], ['PERSON', 'ORG', 1]]; the two count-2 rows are swapped.
- **Location:** `spanalign/reports.py` → `rank_confusions`
- **Why it fails:** most_common() orders by count only and keeps first-seen order among equal counts. ann-a's ORG→LOC confusion comes first in the file, so it is listed before LOC→ORG instead of after it alphabetically.
- **Failing test:** `test_2_scores.TestAgreementReport.test_label_confusions`
- **Unblocks:** test_2 test_label_confusions.

Fix:

```diff
-    ranked = counts.most_common()
+    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
```

Observed with only this bug applied (`tests.test_2_scores.TestAgreementReport.test_label_confusions`):

```
AssertionError: Lists differ: [['ORG', 'LOC', 2], ['LOC', 'ORG', 2], ['PERSON', 'ORG', 1]] != [['LOC', 'ORG', 2], ['ORG', 'LOC', 2], ['PERSON', 'ORG', 1]]

First differing element 0:
['ORG', 'LOC', 2]
['LOC', 'ORG', 2]

- [['ORG', 'LOC', 2], ['LOC', 'ORG', 2], ['PERSON', 'ORG', 1]]
+ [['LOC', 'ORG', 2], ['ORG', 'LOC', 2], ['PERSON', 'ORG', 1]]
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `spanalign/tokens.py` → `tokenize`: finditer's m.end() is already end-exclusive, matching the span convention, and the pattern keeps inner apostrophes (O'Brien) and splits punctuation into single tokens exactly as the README describes.
- `spanalign/spans.py` → `trim_whitespace`: The arithmetic looks backwards, but lstrip measures the leading whitespace (added to start) and rstrip the trailing whitespace (subtracted from end). An all-whitespace selection makes start >= end and is rejected as empty.
