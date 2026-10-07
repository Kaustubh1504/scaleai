# set-031 answer key: Multiple-choice eval scoring with retried attempts

**Domain:** llm_eval_scoring  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_scoring.TestScoring.test_accuracy`
- `tests.test_1_scoring.TestScoring.test_correct_items`
- `tests.test_1_scoring.TestScoring.test_unparsed_and_failed`
- `tests.test_2_report.TestReport.test_by_category`
- `tests.test_2_report.TestReport.test_status_counts`

## Bugs (recommended order)

### B1: Status enum compared to plain strings

- **Type:** enum-vs-string
- **Symptom:** Test 1: test_correct_items loses atlas Q08 and boreal Q11; test_unparsed_and_failed shows atlas unparsed [Q04, Q05, Q06, Q08] and both failed lists empty; accuracy 0.552 / 0.586. Test 2: test_by_category shows atlas logic 0.5 (boreal logic 0.25).
- **Location:** `evalscore/scoring.py` → `select_final`
- **Why it fails:** Attempt.status holds a Status enum member, and a plain Enum never equals its value string, so the filter never skips anything. The highest-numbered attempt is graded even when it errored or timed out.
- **Unblocks:** test_correct_items, test_unparsed_and_failed and test_by_category; exposes B3 in test_accuracy.

Fix:

```diff
# evalscore/scoring.py
-        if att.status in ("error", "timeout"):
+        if att.status in (Status.ERROR, Status.TIMEOUT):

# evalscore/scoring.py
-from .models import ModelScore
+from .models import ModelScore, Status
```

Observed with only this bug applied (`tests.test_1_scoring.TestScoring.test_accuracy`):

```
AssertionError: {'atlas-7b': 0.552, 'boreal-13b': 0.586} != {'atlas-7b': 0.621, 'boreal-13b': 0.655}
- {'atlas-7b': 0.552, 'boreal-13b': 0.586}
?                ^^                    ^^

+ {'atlas-7b': 0.621, 'boreal-13b': 0.655}
?                ^ +                  + ^
```

### B2: Timeout check always true

- **Type:** or-precedence
- **Symptom:** Test 2 only: test_status_counts shows error 0 and timeout 6 for both models (should be error 4, timeout 2).
- **Location:** `evalscore/loader.py` → `parse_status`
- **Why it fails:** `text == "timeout" or "timed_out"` parses as `(text == "timeout") or "timed_out"`, and a non-empty string is truthy, so every non-ok status becomes TIMEOUT. Grading is unaffected because both error and timeout are skipped, so only the counts show it.
- **Unblocks:** test_status_counts.

Fix:

```diff
-    if text == "timeout" or "timed_out":
+    if text == "timeout" or text == "timed_out":
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_status_counts`):

```
AssertionError: {'atl[23 chars]or': 0, 'timeout': 6}, 'boreal-13b': {'ok': 11[23 chars]: 6}} != {'atl[23 chars]or': 4, 'timeout': 2}, 'boreal-13b': {'ok': 11[23 chars]: 2}}
- {'atlas-7b': {'error': 0, 'ok': 11, 'timeout': 6},
?                        ^                       ^

+ {'atlas-7b': {'error': 4, 'ok': 11, 'timeout': 2},
?                        ^                       ^

-  'boreal-13b':  ...
```

### B3: Failed items dropped from the denominator

- **Type:** counting-wrong-subset
- **Symptom:** Only visible after B1 is fixed. Test 1 test_accuracy: atlas 0.692 and boreal 0.76 instead of 0.621 / 0.655. Correct lists and by_category are fine.
- **Location:** `evalscore/scoring.py` → `score_model`
- **Why it fails:** The weight is only added to `possible` after the failed check's `continue`, so items with no ok attempt vanish from the denominator. README rule 7 keeps them in.
- **Unblocks:** test_accuracy.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
+        score.possible += item.weight
         final = select_final(by_item.get(item.item_id, []))
         if final is None:
             score.failed.append(item.item_id)
             continue
-        score.possible += item.weight
```

Observed with only this bug applied (`tests.test_1_scoring.TestScoring.test_accuracy`):

```
AssertionError: {'atlas-7b': 0.692, 'boreal-13b': 0.76} != {'atlas-7b': 0.621, 'boreal-13b': 0.655}
- {'atlas-7b': 0.692, 'boreal-13b': 0.76}
?                 -                   -

+ {'atlas-7b': 0.621, 'boreal-13b': 0.655}
?                  +                   ++
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `evalscore/parsing.py` → `parse_choice`: Taking matches[-1] looks like it should be the first match, but README rule 3 says the last Answer marker wins because models revise themselves. The negative lookahead stops words like 'Definitely' from being read as a D, and the bare-letter fallback uses fullmatch so it only fires on outputs that are a lone letter.
