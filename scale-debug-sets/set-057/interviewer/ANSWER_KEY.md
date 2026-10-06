# set-057 answer key: NER span adjudication: legacy offsets, voting, overlaps

**Domain:** ner_spans  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_adjudication.TestAdjudication.test_legacy_tool_offsets` | B1 Legacy end shifted as if it were 1-based exclusive |
| `test_1_adjudication.TestAdjudication.test_overlapping_spans` | B2 Equal-vote overlaps not ranked by length |
| `test_2_summary.TestSummary.test_named_entities` | B3 `== "PER" or "ORG"` counts every entity |

## Failing pattern with all bugs present

- `tests.test_1_adjudication.TestAdjudication.test_legacy_tool_offsets`
- `tests.test_1_adjudication.TestAdjudication.test_overlapping_spans`
- `tests.test_2_summary.TestSummary.test_named_entities`

## Bugs (recommended order)

### B1: Legacy end shifted as if it were 1-based exclusive

- **Type:** span-offset-off-by-one
- **Symptom:** test_1_adjudication.test_legacy_tool_offsets: D04 comes out as [[13, 17, 'LOC', 'Pari'], [37, 43, 'DATE', '12 Jun']]; every legacy span is one character short and Lima is missing.
- **Location:** `spanmerge/loader.py` → `to_zero_based`
- **Why it fails:** A 1-based inclusive end is numerically the same as a 0-based exclusive end, so only start needs shifting. Subtracting 1 from end too cuts the last character off every legacy span (Paris -> Pari), which also breaks agreement with the v2 annotator.
- **Failing test:** `test_1_adjudication.TestAdjudication.test_legacy_tool_offsets`
- **Unblocks:** test_legacy_tool_offsets.

Fix:

```diff
-        return start - 1, end - 1
+        return start - 1, end
```

Observed with only this bug applied (`tests.test_1_adjudication.TestAdjudication.test_legacy_tool_offsets`):

```
AssertionError: Lists differ: [[13, 17, 'LOC', 'Pari'], [37, 43, 'DATE', '12 Jun']] != [[13, 18, 'LOC', 'Paris'], [22, 26, 'LOC', 'Lima'], [37, 44, 'DATE', '12 June']]

First differing element 0:
[13, 17, 'LOC', 'Pari']
[13, 18, 'LOC', 'Paris']

Second list contains 1 additional elements.
First extra element 2:
[37, 44, 'DATE', '12 June']

- [[13, 17, 'LOC', 'Pari'], [37, 43, 'DATE', '12 Jun']]
?  ...
```

### B2: Equal-vote overlaps not ranked by length

- **Type:** wrong-tie-break
- **Symptom:** test_1_adjudication.test_overlapping_spans: D02's first entity is [4, 10, 'PER', 'Morgan'] instead of [4, 18, 'ORG', 'Morgan Stanley'].
- **Location:** `spanmerge/resolve.py` → `resolve_doc`
- **Why it fails:** Morgan Stanley (ORG) and Morgan (PER) both have 2 votes and the same start. Without the length key the stable sort keeps the candidates' offset order, where the shorter span comes first, so PER 'Morgan' is kept.
- **Failing test:** `test_1_adjudication.TestAdjudication.test_overlapping_spans`
- **Unblocks:** test_overlapping_spans.

Fix:

```diff
-    for ent in sorted(entities, key=lambda e: (-e.votes, e.start)):
+    for ent in sorted(entities, key=lambda e: (-e.votes, -e.length, e.start)):
```

Observed with only this bug applied (`tests.test_1_adjudication.TestAdjudication.test_overlapping_spans`):

```
AssertionError: Lists differ: [[4, 10, 'PER', 'Morgan'], [29, 35, 'LOC', 'Bos[27 chars]19']] != [[4, 18, 'ORG', 'Morgan Stanley'], [29, 35, 'LO[35 chars]19']]

First differing element 0:
[4, 10, 'PER', 'Morgan']
[4, 18, 'ORG', 'Morgan Stanley']

- [[4, 10, 'PER', 'Morgan'], [29, 35, 'LOC', 'Boston'], [46, 50, 'DATE', '2019']]
+ [[4, 18, 'ORG', 'Morgan Stanley'],
+  [29, 35, 'LOC', 'Boston'],
+  [4 ...
```

### B3: `== "PER" or "ORG"` counts every entity

- **Type:** or-precedence
- **Symptom:** test_2_summary.test_named_entities: 14 != 6 (every kept entity is counted).
- **Location:** `spanmerge/reports.py` → `build_report`
- **Why it fails:** `ent[2] == "PER" or "ORG"` parses as `(ent[2] == "PER") or "ORG"`, and the non-empty string is always truthy, so LOC and DATE entities are counted too.
- **Failing test:** `test_2_summary.TestSummary.test_named_entities`
- **Unblocks:** test_named_entities.

Fix:

```diff
-if ent[2] == "PER" or "ORG")
+if ent[2] == "PER" or ent[2] == "ORG")
```

Observed with only this bug applied (`tests.test_2_summary.TestSummary.test_named_entities`):

```
AssertionError: 14 != 6
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `spanmerge/spans.py` → `trim_span`: `text[end - 1]` looks like an off-by-one, but end is exclusive, so the last character of the span is at end - 1. Both loops stop when start meets end, so an all-whitespace span collapses to empty and is dropped by make_span.
