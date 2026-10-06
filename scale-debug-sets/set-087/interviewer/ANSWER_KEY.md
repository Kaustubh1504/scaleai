# set-087 answer key: Chat SFT packer with per-source token budgets

**Domain:** sft_formatting  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_examples.TestExamples.test_1_late_system_turn` | B1 Late system turn ends the conversation |
| `test_1_examples.TestExamples.test_2_vendor_b_example` | B2 Example exactly at budget gets trimmed |
| `test_2_report.TestReport.test_3_tag_counts` | B3 Blank tag pieces counted as a tag |

## Failing pattern with all bugs present

- `tests.test_1_examples.TestExamples.test_1_late_system_turn`
- `tests.test_1_examples.TestExamples.test_2_vendor_b_example`
- `tests.test_2_report.TestReport.test_3_tag_counts`

## Bugs (recommended order)

### B1: Late system turn ends the conversation

- **Type:** early-return
- **Symptom:** test_1_late_system_turn fails: c06 has roles [system, user, assistant], 31 tokens, dropped_pairs 0; expected both pairs and 48 tokens.
- **Location:** `chatpack/formatting.py` → `normalise_turns`
- **Why it fails:** Spec rule 2 drops only the late system turn and keeps everything after it. `break` stops reading the conversation at the first late system turn, so c06 loses its second pair. It still has a valid pair and fits its budget, so nothing else notices.
- **Failing test:** `test_1_examples.TestExamples.test_1_late_system_turn`
- **Unblocks:** test_1_late_system_turn (c06 keeps both pairs, 48 tokens).

Fix:

```diff
         if role == "system" and turns:
-            break
+            continue
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_1_late_system_turn`):

```
AssertionError: {'sou[52 chars]tant'], 'tokens': 31, 'dropped_pairs': 0, 'tex[150 chars]d|>'} != {'sou[52 chars]tant', 'user', 'assistant'], 'tokens': 48, 'dr[254 chars]d|>'}
Diff is 666 characters long. Set self.maxDiff to None to see it.
```

### B2: Example exactly at budget gets trimmed

- **Type:** off-by-one
- **Symptom:** test_2_vendor_b_example fails: c09 comes out as (tokens, dropped_pairs) = (32, 1) instead of (64, 0).
- **Location:** `chatpack/budget.py` → `fit_budget`
- **Why it fails:** The spec keeps an example that is at or under the budget. `>=` keeps trimming when the total equals the budget, so c09 (exactly 64 tokens against vendor-b's default 64) loses its first pair.
- **Failing test:** `test_1_examples.TestExamples.test_2_vendor_b_example`
- **Unblocks:** test_2_vendor_b_example (c09 stays at 64 tokens with 0 dropped pairs).

Fix:

```diff
-    while total >= budget and start < len(pairs) - 1:
+    while total > budget and start < len(pairs) - 1:
```

Observed with only this bug applied (`tests.test_1_examples.TestExamples.test_2_vendor_b_example`):

```
AssertionError: Tuples differ: (32, 1) != (64, 0)

First differing element 0:
32
64

- (32, 1)
+ (64, 0)
```

### B3: Blank tag pieces counted as a tag

- **Type:** empty-split
- **Symptom:** test_3_tag_counts fails: tag_counts has an extra '': 3 entry; all real tag counts are as expected.
- **Location:** `chatpack/loader.py` → `parse_tags`
- **Why it fails:** `"".split(";")` returns `[""]`, and `"a;;b"` or `"cooking;"` also produce empty pieces. Without the filter, every blank or doubled separator adds an empty-string tag, which shows up as `"": 3` in tag_counts.
- **Failing test:** `test_2_report.TestReport.test_3_tag_counts`
- **Unblocks:** test_3_tag_counts.

Fix:

```diff
-    return [p.strip().lower() for p in clean(raw).split(";")]
+    parts = [p.strip().lower() for p in clean(raw).split(";")]
+    return [p for p in parts if p]
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_3_tag_counts`):

```
AssertionError: {'': 3, 'billing': 1, 'chitchat': 1, 'code'[129 chars]': 1} != {'billing': 1, 'chitchat': 1, 'code': 1, 'c[122 chars]': 1}
- {'': 3,
-  'billing': 1,
? ^

+ {'billing': 1,
? ^

   'chitchat': 1,
   'code': 1,
   'cooking': 1,
   'general': 1,
   'greeting': 1,
   'math': 1,
   'news': 1,
   'qa': 1,
   'review': 1,
   'summarize': 1,
   'support': 2,
   'travel': 1}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `chatpack/budget.py` → `count_tokens`: `str.split()` with no argument splits on runs of whitespace and returns [] for an empty string, so it counts words correctly, including the `\n` that merged turns contain. Candidates who just saw the tag `split(';')` issue often suspect this too.
- `chatpack/formatting.py` → `merge_consecutive`: It replaces merged[-1] with a new frozen Turn instead of mutating a shared object, and joins contents with `\n` exactly as the spec says. It runs after late system turns are removed, so two user turns separated by a dropped system turn are merged, which is what the spec order implies.
