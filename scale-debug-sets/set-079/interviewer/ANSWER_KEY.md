# set-079 answer key: LLM judge score rollup: parsing, medians, weighted leaderboard

**Domain:** llm_eval_scoring  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_judgments.TestJudgments.test_parse_failures` | B1 Malformed JSONL line silently skipped |
| `test_2_leaderboard.TestLeaderboard.test_leaderboard` | B2 Leaderboard averages display-rounded scores |
| `test_2_leaderboard.TestLeaderboard.test_categories` | B3 group_by's default dict shared across calls |

## Failing pattern with all bugs present

- `tests.test_1_judgments.TestJudgments.test_parse_failures`
- `tests.test_2_leaderboard.TestLeaderboard.test_categories`
- `tests.test_2_leaderboard.TestLeaderboard.test_leaderboard`

## Bugs (recommended order)

### B1: Malformed JSONL line silently skipped

- **Type:** swallowed-exception
- **Symptom:** Test 1 test_parse_failures: `['j10', 'j15', 'j32', 'j34'] != [..., 'line-21']`. The truncated line 21 is missing from the failures. Sample scores are unchanged.
- **Location:** `judgescore/loader.py` → `load_judgments`
- **Why it fails:** Line 21 is truncated JSON. The except branch drops it without recording a failure, so the error is swallowed. s11 still scores 0.67 from its other judge, so nothing else changes.
- **Failing test:** `test_1_judgments.TestJudgments.test_parse_failures`
- **Unblocks:** test_parse_failures

Fix:

```diff
             except json.JSONDecodeError:
+                failures.append(f"line-{n}")
                 continue
```

Observed with only this bug applied (`tests.test_1_judgments.TestJudgments.test_parse_failures`):

```
AssertionError: Lists differ: ['j10', 'j15', 'j32', 'j34'] != ['j10', 'j15', 'j32', 'j34', 'line-21']

Second list contains 1 additional elements.
First extra element 4:
'line-21'

- ['j10', 'j15', 'j32', 'j34']
+ ['j10', 'j15', 'j32', 'j34', 'line-21']
?                            +++++++++++
```

### B2: Leaderboard averages display-rounded scores

- **Type:** float-rounding
- **Symptom:** Test 2 test_leaderboard: `{'atlas-7b': 0.678, 'borealis-13b': 0.68, 'cirrus-70b': 0.775}` instead of 0.679 / 0.681 / 0.776. The ranking order is unchanged.
- **Location:** `judgescore/reports.py` → `build_report`
- **Why it fails:** `shown` holds scores rounded to 2 decimals for display. Averaging those piles up rounding error (0.8333 becomes 0.83, 0.6667 becomes 0.67), so the leaderboard moves by about 0.001. The spec rounds only the final values.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_leaderboard`
- **Unblocks:** test_leaderboard

Fix:

```diff
-weighted_mean(by_model[m], shown, weights)
+weighted_mean(by_model[m], scores, weights)
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_leaderboard`):

```
AssertionError: {'atlas-7b': 0.678, 'borealis-13b': 0.68, 'cirrus-70b': 0.775} != {'atlas-7b': 0.679, 'borealis-13b': 0.681, 'cirrus-70b': 0.776}
- {'atlas-7b': 0.678, 'borealis-13b': 0.68, 'cirrus-70b': 0.775}
?                  ^                                          ^

+ {'atlas-7b': 0.679, 'borealis-13b': 0.681, 'cirrus-70b': 0.776}
?                  ^                      +                ...
```

### B3: group_by's default dict shared across calls

- **Type:** mutable-default
- **Symptom:** Test 2 test_categories: the table starts with model keys, e.g. `{'atlas-7b': {'n': 12, 'mean': 0.706}, 'borealis-13b': ...}`, ahead of the real categories. In a full-suite run the `n` values are doubled, because the shared dict also kept test_1's run. The leaderboard is unaffected.
- **Location:** `judgescore/aggregate.py` → `group_by`
- **Why it fails:** The default dict is created once, when the function is defined. The model grouping and the category grouping (and every later build_report run) fill the same dict, so the category table also gets model keys. The leaderboard looks fine because it only reads its own model keys, and duplicated lists don't change a mean.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_categories`
- **Unblocks:** test_categories

Fix:

```diff
-def group_by(items, key, into={}):
+def group_by(items, key, into=None):
     """Group items by key(item), appending to `into` when one is given."""
-    groups = into
+    groups = {} if into is None else into
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_categories`):

```
AssertionError: {'atlas-7b': {'n': 12, 'mean': 0.706}, 'bor[223 chars]656}} != {'coding': {'n': 6, 'mean': 0.669}, 'reason[101 chars]656}}
Diff is 769 characters long. Set self.maxDiff to None to see it.
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `judgescore/parsing.py` → `extract_fraction`: The regex looks fragile, but it accepts both 'Score' and 'Rating', ':' or '=', decimals and spaces around '/', and requires the keyword. That is exactly README rule 2, and every fraction-style reply in the data parses.
- `judgescore/aggregate.py` → `median`: `(n - 1) // 2` looks like an off-by-one, but for odd n it is the middle index and for even n it is the lower of the two middle indices, which are then averaged. For n = 2 that gives the mean of both, and for n = 1 the single value.
