# set-055 answer key: Multiple-choice eval scorer: retries, answer extraction, weighted leaderboard

**Domain:** llm_eval_scoring  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_grading.TestGrading.test_unscored_items` | B1 `== "ok" or "cached"` is always true |
| `test_2_report.TestReport.test_weighted_scores` | B2 Zero weight replaced by the default |
| `test_2_report.TestReport.test_leaderboard` | B3 Score ties broken by name only |

## Failing pattern with all bugs present

- `tests.test_1_grading.TestGrading.test_unscored_items`
- `tests.test_2_report.TestReport.test_leaderboard`
- `tests.test_2_report.TestReport.test_weighted_scores`

## Bugs (recommended order)

### B1: `== "ok" or "cached"` is always true

- **Type:** or-precedence
- **Symptom:** Test 1 test_unscored_items: delta shows errored [] and unparsed ['I05', 'I07', 'I09'] instead of errored ['I05', 'I09'] and unparsed ['I07'].
- **Location:** `evalscore/grading.py` → `latest_success`
- **Why it fails:** This parses as `(status == 'ok') or 'cached'`, and the non-empty string is truthy, so every attempt counts as successful. delta's I05/I09 then use a timeout/rate-limited attempt, whose output has no answer, and they move from errored to unparsed.
- **Failing test:** `test_1_grading.TestGrading.test_unscored_items`
- **Unblocks:** test_unscored_items.

Fix:

```diff
-        if att.status == "ok" or "cached":
+        if att.status in ("ok", "cached"):
```

Observed with only this bug applied (`tests.test_1_grading.TestGrading.test_unscored_items`):

```
AssertionError: {'alp[121 chars]}, 'delta': {'errored': [], 'unparsed': ['I05', 'I07', 'I09']}} != {'alp[121 chars]}, 'delta': {'errored': ['I05', 'I09'], 'unparsed': ['I07']}}
  {'alpha': {'errored': [], 'unparsed': []},
   'bravo': {'errored': [], 'unparsed': []},
   'charlie': {'errored': [], 'unparsed': []},
-  'delta': {'errored': [], 'unparsed': ['I05', 'I07', 'I09']}}
?                      ...
```

### B2: Zero weight replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 2 test_weighted_scores: {'alpha': 0.8, 'bravo': 0.5, 'charlie': 0.5, 'delta': 0.15} instead of 0.833 / 0.556 / 0.556 / 0.167. The leaderboard order is unchanged.
- **Location:** `evalscore/loader.py` → `load_items`
- **Why it fails:** `weight or DEFAULT_WEIGHT` treats a real 0 like a blank, so the two calibration items count 1 point each. The total becomes 20 instead of 18, and alpha also gains a point for I06.
- **Failing test:** `test_2_report.TestReport.test_weighted_scores`
- **Unblocks:** test_weighted_scores.

Fix:

```diff
-                weight=weight or DEFAULT_WEIGHT,
+                weight=DEFAULT_WEIGHT if weight is None else weight,
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_weighted_scores`):

```
AssertionError: {'alpha': 0.8, 'bravo': 0.5, 'charlie': 0.5, 'delta': 0.15} != {'alpha': 0.833, 'bravo': 0.556, 'charlie': 0.556, 'delta': 0.167}
- {'alpha': 0.8, 'bravo': 0.5, 'charlie': 0.5, 'delta': 0.15}
?                                                          ^

+ {'alpha': 0.833, 'bravo': 0.556, 'charlie': 0.556, 'delta': 0.167}
?              ++              ++                ++           ...
```

### B3: Score ties broken by name only

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_leaderboard: ['alpha', 'bravo', 'charlie', 'delta'] instead of ['alpha', 'charlie', 'bravo', 'delta'].
- **Location:** `evalscore/reports.py` → `build_report`
- **Why it fails:** bravo and charlie are tied at 0.556. The README breaks ties by more correct items first (charlie has 7, bravo 4), and only then by name.
- **Failing test:** `test_2_report.TestReport.test_leaderboard`
- **Unblocks:** test_leaderboard.

Fix:

```diff
-    leaderboard = sorted(scores, key=lambda m: (-scores[m], m))
+    leaderboard = sorted(scores, key=lambda m: (-scores[m], -len(correct[m]), m))
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_leaderboard`):

```
AssertionError: Lists differ: ['alpha', 'bravo', 'charlie', 'delta'] != ['alpha', 'charlie', 'bravo', 'delta']

First differing element 1:
'bravo'
'charlie'

- ['alpha', 'bravo', 'charlie', 'delta']
?          ---------

+ ['alpha', 'charlie', 'bravo', 'delta']
?                      +++++++++
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `evalscore/parsing.py` → `extract_choice`: Taking matches[-1] looks backwards, but the README says the last answer marker wins. delta's I08 ('First guess: answer is A. On reflection, Answer = C') depends on it. JSON is only tried when the output starts with '{', as the spec says.
