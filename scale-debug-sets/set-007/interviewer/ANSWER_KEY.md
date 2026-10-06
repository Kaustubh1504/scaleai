# set-007 answer key: Multiple-choice eval scorer with weighted accuracy

**Domain:** llm_eval_scoring  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_grading.TestGrading.test_flags` | B1 Flag list is a shared default |
| `test_2_report.TestReport.test_by_category` | B2 Category counter fed a string |
| `test_2_report.TestReport.test_leaderboard` | B3 Accuracy ties broken by name only |

## Failing pattern with all bugs present

- `tests.test_1_grading.TestGrading.test_flags`
- `tests.test_2_report.TestReport.test_by_category`
- `tests.test_2_report.TestReport.test_leaderboard`

## Bugs (recommended order)

### B1: Flag list is a shared default

- **Type:** mutable-default
- **Symptom:** Test 1 test_flags: every response, including clean ones like r01, has the same six-entry list ['multiple_answers', 'no_answer', 'no_answer', 'multiple_answers', 'multiple_answers', 'no_answer'].
- **Location:** `evalscore/parsing.py` → `parse_output`
- **Why it fails:** A default value is evaluated once, when the function is defined. Every call that doesn't pass `flags` appends to the same list, and every graded response holds a reference to it, so all 36 responses end up with all six flags.
- **Failing test:** `test_1_grading.TestGrading.test_flags`
- **Unblocks:** test_1_grading.TestGrading.test_flags.

Fix:

```diff
-def parse_output(text, flags=[]):
+def parse_output(text, flags=None):
     """Return (answer letter or None, flags) for one model output."""
+    flags = [] if flags is None else flags
```

Observed with only this bug applied (`tests.test_1_grading.TestGrading.test_flags`):

```
AssertionError: {'r01': ['multiple_answers', 'no_answer', 'no[3838 chars]er']} != {'r03': ['multiple_answers'], 'r06': ['no_ans[103 chars]er']}
Diff is 6362 characters long. Set self.maxDiff to None to see it.
```

### B2: Category counter fed a string

- **Type:** counter-misuse
- **Symptom:** Test 2 test_by_category: keys are single letters ({'a': 6, 'c': 2, 'd': 3, 'e': 3, 'g': 5, ...}) instead of logic/math/reading.
- **Location:** `evalscore/scoring.py` → `model_stats`
- **Why it fails:** `Counter.update` iterates its argument, and iterating a string yields its characters. Each correct response adds one count per letter of `math`, `logic` or `reading` instead of one count for the category.
- **Failing test:** `test_2_report.TestReport.test_by_category`
- **Unblocks:** test_2_report.TestReport.test_by_category.

Fix:

```diff
-                by_category.update(r["category"])
+                by_category[r["category"]] += 1
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_by_category`):

```
AssertionError: {'atlas-7b': {'a': 6, 'c': 2, 'd': 3, 'e': 3, 'g': 5, 'h[298 chars]: 2}} != {'atlas-7b': {'logic': 2, 'math': 3, 'reading': 3}, 'bor[97 chars]: 2}}
Diff is 1171 characters long. Set self.maxDiff to None to see it.
```

### B3: Accuracy ties broken by name only

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_leaderboard: ['atlas-7b', 'borealis-13b', 'cirrus-3b'] instead of ['borealis-13b', 'atlas-7b', 'cirrus-3b'].
- **Location:** `evalscore/reports.py` → `leaderboard`
- **Why it fails:** atlas-7b and borealis-13b both score 0.7. The spec breaks that tie on lower mean latency (borealis, 850.0 ms) before name, but the sort key skips latency and goes straight to the name.
- **Failing test:** `test_2_report.TestReport.test_leaderboard`
- **Unblocks:** test_2_report.TestReport.test_leaderboard.

Fix:

```diff
-    ranked = sorted(stats.items(), key=lambda kv: (-kv[1]["accuracy"], kv[0]))
+    ranked = sorted(stats.items(), key=lambda kv: (-kv[1]["accuracy"], kv[1]["mean_latency_ms"], kv[0]))
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_leaderboard`):

```
AssertionError: Lists differ: ['atlas-7b', 'borealis-13b', 'cirrus-3b'] != ['borealis-13b', 'atlas-7b', 'cirrus-3b']

First differing element 0:
'atlas-7b'
'borealis-13b'

- ['atlas-7b', 'borealis-13b', 'cirrus-3b']
+ ['borealis-13b', 'atlas-7b', 'cirrus-3b']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `evalscore/parsing.py` → `last_answer`: Taking `matches[-1]` looks like it might skip the model's first answer, but README rule 2 says the last tag is the answer. r03, r23 and r35 revise themselves and are graded on the final letter.
