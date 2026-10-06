# set-063 answer key: Chat-format SFT export with a token budget

**Domain:** sft_formatting  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_examples.TestExamples.test_example_ids`
- `tests.test_1_examples.TestExamples.test_example_tags`
- `tests.test_1_examples.TestExamples.test_token_counts`
- `tests.test_1_examples.TestExamples.test_truncated_examples`
- `tests.test_2_summary.TestSummary.test_example_count`
- `tests.test_2_summary.TestSummary.test_rejections`
- `tests.test_2_summary.TestSummary.test_tag_counts`
- `tests.test_2_summary.TestSummary.test_total_tokens`

## Bugs (recommended order)

### B1: Blank tag cells produce an empty tag

- **Type:** empty-split
- **Symptom:** Test 1 test_example_tags: c02 and c09 have tags [""] instead of ["general"], and c08 has an extra "". Test 2 test_tag_counts: an empty-string key with count 3 appears and general is missing.
- **Location:** `turnsmith/loader.py` → `parse_tags`
- **Why it fails:** `"".split(";")` is `[""]`, not `[]`. A blank cell becomes a one-element list holding an empty tag, which is truthy, so the `general` default never applies; the trailing `;` on c08 adds an empty tag too.
- **Unblocks:** test_example_tags and test_tag_counts.

Fix:

```diff
-    return [t.strip().lower() for t in clean(raw).split(";")]
+    return [t.strip().lower() for t in clean(raw).split(";") if t.strip()]
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_example_tags`):

```
AssertionError: {'c01[20 chars]': [''], 'c03': ['shipping', 'returns'], 'c05'[77 chars]ng']} != {'c01[20 chars]': ['general'], 'c03': ['shipping', 'returns'][87 chars]ng']}
  {'c01': ['billing'],
-  'c02': [''],
+  'c02': ['general'],
?           +++++++

   'c03': ['shipping', 'returns'],
   'c05': ['returns'],
-  'c08': ['coding', 'billing', ''],
?                             ----

+  'c08': ['c ...
```

### B2: Budget loop config reads the generation limit

- **Type:** wrong-field
- **Symptom:** Test 1: c07 shows up as an example, c03 has 86 tokens and c10 73 (no truncation, dropped_messages 0). Test 2: c07 is missing from rejected, examples is 8, coding counts 2 and total_tokens is 417 instead of 295.
- **Location:** `turnsmith/loader.py` → `load_config`
- **Why it fails:** The export budget is taken from `max_new_tokens` (256) instead of `max_tokens` (60). Nothing exceeds 256, so c03 and c10 are never truncated and c07 is accepted instead of rejected as too_long.
- **Unblocks:** The token, truncation and rejection tests, and it exposes B3.

Fix:

```diff
-        "max_tokens": int(raw["max_new_tokens"]),
+        "max_tokens": int(raw["max_tokens"]),
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_example_ids`):

```
AssertionError: Lists differ: ['c01', 'c02', 'c03', 'c05', 'c07', 'c08', 'c09', 'c10'] != ['c01', 'c02', 'c03', 'c05', 'c08', 'c09', 'c10']

First differing element 4:
'c07'
'c08'

First list contains 1 additional elements.
First extra element 7:
'c10'

- ['c01', 'c02', 'c03', 'c05', 'c07', 'c08', 'c09', 'c10']
?                              -------

+ ['c01', 'c02', 'c03', 'c05', 'c08', 'c09', 'c ...
```

### B3: Truncation drops one message instead of an exchange

- **Type:** slice-bounds
- **Symptom:** Only visible after B2 is fixed. Test 1: c10 keeps the assistant message "Yes, and no fees." as its first turn (tokens 55 instead of 47) and c03 reports dropped_messages 4 instead of 2. Test 2: total_tokens is 303 instead of 295.
- **Location:** `turnsmith/budget.py` → `fit_to_budget`
- **Why it fails:** Slicing off one message at a time leaves an example that can start with an assistant turn (c10 starts with "Yes, and no fees."), and `dropped` still grows by 2 per step, so c03 reports 4 dropped messages.
- **Unblocks:** test_truncated_examples, test_token_counts and test_total_tokens.
- **Masked:** invisible until B2 is fixed (identical test output either way).

Fix:

```diff
-        body = body[1:]
+        body = body[2:]
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_token_counts`):

```
AssertionError: {'c01': 33, 'c02': 34, 'c03': 59, 'c05': 33, 'c08': 54, 'c09': 35, 'c10': 55} != {'c01': 33, 'c02': 34, 'c03': 59, 'c05': 33, 'c08': 54, 'c09': 35, 'c10': 47}
- {'c01': 33, 'c02': 34, 'c03': 59, 'c05': 33, 'c08': 54, 'c09': 35, 'c10': 55}
?                                                                           ^^

+ {'c01': 33, 'c02': 34, 'c03': 59, 'c05': 33, 'c08': 54, 'c09':  ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `turnsmith/budget.py` → `count_tokens`: `str.split()` with no argument splits on any whitespace run and returns [] for an empty string, so it counts words exactly as rule 5 says. It looks like a cousin of the tag-splitting code, but only `split(";")` produces empty entries.
