# set-039 answer key: SFT formatter: trimming, loss-mask spans, role enums

**Domain:** sft_formatting  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_render.TestRender.test_assistant_spans` | B1 Assistant span starts on the header newline |
| `test_1_render.TestRender.test_truncation` | B2 Trimming edits the caller's message list |
| `test_2_report.TestReport.test_assistant_turns` | B3 Role enum compared with a string |

## Failing pattern with all bugs present

- `tests.test_1_render.TestRender.test_assistant_spans`
- `tests.test_1_render.TestRender.test_truncation`
- `tests.test_2_report.TestReport.test_assistant_turns`

## Bugs (recommended order)

### B1: Assistant span starts on the header newline

- **Type:** span-offset-off-by-one
- **Symptom:** Test 1 test_assistant_spans: c03 spans are [[105, 109], [160, 164]] instead of [[106, 110], [161, 165]]. Every span is shifted one character left (text[s:e] would be "\nCat" instead of "Cat.").
- **Location:** `sftfmt/masks.py` → `assistant_spans`
- **Why it fails:** The header is the tag plus a newline. Starting at offset + len(tag) puts the span on the '\n', and because end is start + len(content), the last character of the content falls outside the span.
- **Failing test:** `test_1_render.TestRender.test_assistant_spans`
- **Unblocks:** Test 1 test_assistant_spans.

Fix:

```diff
-            start = offset + len(tag(message))
+            start = offset + len(tag(message)) + 1
```

Observed with only this bug applied (`tests.test_1_render.TestRender.test_assistant_spans`):

```
AssertionError: Lists differ: [[105, 109], [160, 164]] != [[106, 110], [161, 165]]

First differing element 0:
[105, 109]
[106, 110]

- [[105, 109], [160, 164]]
?     ^    -      ^    ^

+ [[106, 110], [161, 165]]
?     ^  +        ^    ^
```

### B2: Trimming edits the caller's message list

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 1 test_truncation: c07 and c13 show turns_dropped 0 instead of 2, while their token counts (20, 26) are already the trimmed values.
- **Location:** `sftfmt/render.py` → `truncate`
- **Why it fails:** kept is the same list object as messages, so `del kept[...]` also shrinks the caller's list. build_examples then computes turns_dropped = len(messages) - len(kept) = 0, since both names point at the trimmed list.
- **Failing test:** `test_1_render.TestRender.test_truncation`
- **Unblocks:** Test 1 test_truncation.

Fix:

```diff
-    kept = messages
+    kept = list(messages)
```

Observed with only this bug applied (`tests.test_1_render.TestRender.test_truncation`):

```
AssertionError: {'c07': (20, 0), 'c09': (32, 0), 'c13': (26, 0)} != {'c07': (20, 2), 'c09': (32, 0), 'c13': (26, 2)}
- {'c07': (20, 0), 'c09': (32, 0), 'c13': (26, 0)}
?              ^                               ^

+ {'c07': (20, 2), 'c09': (32, 0), 'c13': (26, 2)}
?              ^                               ^
```

### B3: Role enum compared with a string

- **Type:** enum-vs-string
- **Symptom:** Test 2 test_assistant_turns: 0 != 13.
- **Location:** `sftfmt/reports.py` → `summarize`
- **Why it fails:** Role is a plain Enum, so Role.ASSISTANT == 'assistant' is False. The count comes out 0 instead of 13.
- **Failing test:** `test_2_report.TestReport.test_assistant_turns`
- **Unblocks:** Test 2 test_assistant_turns.

Fix:

```diff
# sftfmt/reports.py
-if m.role == "assistant"),
+if m.role is Role.ASSISTANT),

# sftfmt/reports.py
+from .models import Role
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_assistant_turns`):

```
AssertionError: 0 != 13
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `sftfmt/render.py` → `fits`: `<=` looks like a boundary slip, but the README says an example of exactly max_tokens fits. truncate uses fits both for the loop and for the final too_long check, so the boundary is consistent.
