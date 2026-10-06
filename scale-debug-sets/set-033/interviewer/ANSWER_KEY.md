# set-033 answer key: NER span adjudication across two export conventions

**Domain:** ner_spans  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_entities.TestEntities.test_entity_text` | B1 Entity text sliced one character too far |
| `test_1_entities.TestEntities.test_votes` | B2 groupby over a partially sorted list |
| `test_2_annotators.TestAnnotators.test_agreement` | B3 Duplicate submissions counted twice in agreement |

## Failing pattern with all bugs present

- `tests.test_1_entities.TestEntities.test_entity_text`
- `tests.test_1_entities.TestEntities.test_votes`
- `tests.test_2_annotators.TestAnnotators.test_agreement`

## Bugs (recommended order)

### B1: Entity text sliced one character too far

- **Type:** span-offset-off-by-one
- **Symptom:** Test 1 test_entity_text: every entity carries one extra character, e.g. "Angela Merkel ", "Austin.", "Ghent.". Only Kyoto (which ends the text) is unchanged. Offsets and votes are correct.
- **Location:** `spanmerge/reports.py` → `entities_by_doc`
- **Why it fails:** Spans are half-open after loading, so text[start:end] is already the whole entity. Adding 1 treats `end` as inclusive and pulls in the next character (a space or the full stop).
- **Failing test:** `test_1_entities.TestEntities.test_entity_text`
- **Unblocks:** test_entity_text.

Fix:

```diff
-            "text": doc.text[start:end + 1],
+            "text": doc.text[start:end],
```

Observed with only this bug applied (`tests.test_1_entities.TestEntities.test_entity_text`):

```
AssertionError: {'D01[13 chars]erkel ', 'Paris '], 'D02': ['Apple ', 'Austin.[202 chars]to']} != {'D01[13 chars]erkel', 'Paris'], 'D02': ['Apple', 'Austin'], [190 chars]to']}
- {'D01': ['Angela Merkel ', 'Paris '],
?                        -         -

+ {'D01': ['Angela Merkel', 'Paris'],
-  'D02': ['Apple ', 'Austin.'],
?                -          -

+  'D02': ['Apple', 'Austin'],
-  'D03': ['Wa ...
```

### B2: groupby over a partially sorted list

- **Type:** groupby-misuse
- **Symptom:** Test 1 test_votes: D03 shows [2, 2] instead of [3, 2]; Washington lost one PER vote. The entity list itself is unchanged.
- **Location:** `spanmerge/consensus.py` → `vote`
- **Why it fails:** itertools.groupby only merges adjacent items. Sorting by (doc, start) leaves a02's LOC span for 'Washington' between the PER spans, so the PER votes are split into a group of 1 and a group of 2.
- **Failing test:** `test_1_entities.TestEntities.test_votes`
- **Unblocks:** test_votes.

Fix:

```diff
-    ordered = sorted(spans, key=lambda s: (s.doc_id, s.start))
+    ordered = sorted(spans, key=lambda s: s.key)
```

Observed with only this bug applied (`tests.test_1_entities.TestEntities.test_votes`):

```
AssertionError: {'D01[29 chars]3': [2, 2], 'D04': [2, 3], 'D05': [3], 'D06': [46 chars] [2]} != {'D01[29 chars]3': [3, 2], 'D04': [2, 3], 'D05': [3], 'D06': [46 chars] [2]}
  {'D01': [3, 2],
   'D02': [2, 2],
-  'D03': [2, 2],
?          ^

+  'D03': [3, 2],
?          ^

   'D04': [2, 3],
   'D05': [3],
   'D06': [2],
   'D07': [3],
   'D08': [],
   'D09': [2],
   'D10': [2]}
```

### B3: Duplicate submissions counted twice in agreement

- **Type:** missing-dedupe
- **Symptom:** Test 2 test_agreement: a02 is 0.778 instead of 0.75. Every other annotator matches.
- **Location:** `spanmerge/metrics.py` → `agreement`
- **Why it fails:** Collecting keys in a list keeps a02's repeated D05 span twice, in both the hits and the denominator. The README measures agreement over distinct spans.
- **Failing test:** `test_2_annotators.TestAnnotators.test_agreement`
- **Unblocks:** test_agreement.

Fix:

```diff
-    per = defaultdict(list)
+    per = defaultdict(set)
     for span in spans:
-        per[span.annotator].append(span.key)
+        per[span.annotator].add(span.key)
```

Observed with only this bug applied (`tests.test_2_annotators.TestAnnotators.test_agreement`):

```
AssertionError: {'a01': 1.0, 'a02': 0.778, 'a03': 1.0, 'a04': 1.0, 'a05': 1.0, 'a06': 0.714} != {'a01': 1.0, 'a02': 0.75, 'a03': 1.0, 'a04': 1.0, 'a05': 1.0, 'a06': 0.714}
- {'a01': 1.0, 'a02': 0.778, 'a03': 1.0, 'a04': 1.0, 'a05': 1.0, 'a06': 0.714}
?                        ^^

+ {'a01': 1.0, 'a02': 0.75, 'a03': 1.0, 'a04': 1.0, 'a05': 1.0, 'a06': 0.714}
?                        ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `spanmerge/loader.py` → `to_exclusive_end`: The `end + 1` looks like the off-by-one, but the README says labelkit exports the index of the last character, so adding 1 is exactly what turns it into a half-open end. brat ends are already exclusive and pass through unchanged.
