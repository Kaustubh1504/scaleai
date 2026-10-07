# set-015 answer key: SFT chat-template packing with truncation

**Domain:** sft_formatting  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_examples.TestExamples.test_1_outcomes` | B1 Numeric 0 content treated as missing |
| `test_1_examples.TestExamples.test_2_rendered_text` | B2 Rendered parts accumulate across examples |
| `test_2_summary.TestSummary.test_3_tag_counts` | B3 Blank tags counted as a tag |

## Failing pattern with all bugs present

- `tests.test_1_examples.TestExamples.test_1_outcomes`
- `tests.test_1_examples.TestExamples.test_2_rendered_text`
- `tests.test_2_summary.TestSummary.test_3_tag_counts`

## Bugs (recommended order)

### B1: Numeric 0 content treated as missing

- **Type:** falsy-zero
- **Symptom:** SYMPTOM
- **Location:** `sftpack/loader.py` → `clean_content`
- **Why it fails:** `value or ""` replaces every falsy value, so the assistant's numeric answer 0 in c03 becomes an empty string and the conversation is rejected as empty_message. Only None should become empty.
- **Failing test:** `test_1_examples.TestExamples.test_1_outcomes`
- **Unblocks:** test_1_outcomes.

Fix:

```diff
-    return str(value or "").strip()
+    if value is None:
+        return ""
+    return str(value).strip()
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_1_outcomes`):

```
AssertionError: {'c01[32 chars], 'c04': ('ok', 17), 'c05': ('truncated', 35),[33 chars] 30)} != {'c01[32 chars], 'c03': ('ok', 19), 'c04': ('ok', 17), 'c05':[52 chars] 30)}
  {'c01': ('ok', 28),
   'c02': ('ok', 23),
+  'c03': ('ok', 19),
   'c04': ('ok', 17),
   'c05': ('truncated', 35),
   'c11': ('ok', 19),
   'c12': ('ok', 30)}
```

### B2: Rendered parts accumulate across examples

- **Type:** mutable-default
- **Symptom:** SYMPTOM
- **Location:** `sftpack/render.py` → `render`
- **Why it fails:** A default argument is evaluated once, when the function is defined, so every call without `parts` appends to the same list. Each example's text contains every example rendered before it.
- **Failing test:** `test_1_examples.TestExamples.test_2_rendered_text`
- **Unblocks:** test_2_rendered_text.

Fix:

```diff
-def render(messages, parts=[]):
+def render(messages, parts=None):
     """Chat-template text for one example; every assistant turn is closed with <|end|>."""
+    parts = [] if parts is None else parts
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_2_rendered_text`):

```
AssertionError: '<|sy[13 chars]re a careful math tutor.\n<|user|>\nWhat is 12[527 chars]|>\n' != '<|sy[13 chars]re a friendly travel assistant.\n<|user|>\nHow[103 chars]|>\n'
- <|system|>
- You are a careful math tutor.
- <|user|>
- What is 12 times 9?
- <|assistant|>
- 12 times 9 is 108.
- <|end|>
- <|user|>
- How do I reverse a list in Python?
- <|assistant|>
- Use slicing: my_list[::-1] returns ...
```

### B3: Blank tags counted as a tag

- **Type:** empty-split
- **Symptom:** SYMPTOM
- **Location:** `sftpack/reports.py` → `split_tags`
- **Why it fails:** "".split(",") returns [""], not [], and "math,  " gives a blank second piece. Without the filter those blanks are counted as a tag named "".
- **Failing test:** `test_2_summary.TestSummary.test_3_tag_counts`
- **Unblocks:** test_3_tag_counts.

Fix:

```diff
-    return [t.strip().lower() for t in text.split(",")]
+    return [t.strip().lower() for t in text.split(",") if t.strip()]
```

Observed with only this bug applied (`tests.test_2_summary.TestSummary.test_3_tag_counts`):

```
AssertionError: {'': 3, 'chat': 3, 'code': 3, 'long': 1, 'math': 3, 'python': 1, 'safety': 1} != {'chat': 3, 'code': 3, 'long': 1, 'math': 3, 'python': 1, 'safety': 1}
- {'': 3, 'chat': 3, 'code': 3, 'long': 1, 'math': 3, 'python': 1, 'safety': 1}
?  -------

+ {'chat': 3, 'code': 3, 'long': 1, 'math': 3, 'python': 1, 'safety': 1}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `sftpack/turns.py` → `truncate`: `body[2:]` drops exactly one user/assistant pair (the body always alternates after check_order), the system message is kept outside the loop, and `len(body) > 2` stops before the last pair, after which a still-too-long example is rejected, as rules 5 and 6 say.
