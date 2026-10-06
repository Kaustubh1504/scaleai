# set-065 answer key: Benchmark leaderboard with a freeze

**Domain:** leaderboard_ranking  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_scores.TestScores.test_1_team_scores` | B1 Best score picked by string comparison |
| `test_1_scores.TestScores.test_2_tasks_attempted` | B2 Resubmissions counted as extra tasks |
| `test_2_leaderboard.TestLeaderboard.test_3_submission_counts` | B3 Submission at the freeze dropped |

## Failing pattern with all bugs present

- `tests.test_1_scores.TestScores.test_1_team_scores`
- `tests.test_1_scores.TestScores.test_2_tasks_attempted`
- `tests.test_2_leaderboard.TestLeaderboard.test_3_submission_counts`

## Bugs (recommended order)

### B1: Best score picked by string comparison

- **Type:** string-vs-int
- **Symptom:** Test 1 test_1_team_scores: basalt scores 80.67 instead of 81.17 (its gsm8k best stays 98.5 instead of 100.0). Ranks and podiums do not change, so Test 2 still passes.
- **Location:** `podium/scoring.py` → `best_per_task`
- **Why it fails:** Scores are kept as the raw strings from the CSV. Compared as text, "100" sorts before "98.5" because '1' < '9', so basalt's 100 on gsm8k never replaces its earlier 98.5.
- **Failing test:** `test_1_scores.TestScores.test_1_team_scores`
- **Unblocks:** test_1_team_scores.

Fix:

```diff
-        if current is None or s.score > current.score:
+        if current is None or float(s.score) > float(current.score):
```

Observed with only this bug applied (`tests.test_1_scores.TestScores.test_1_team_scores`):

```
AssertionError: {'emb[18 chars]t': 80.67, 'aurora': 80.17, 'cobalt': 80.17, '[109 chars] 0.0} != {'emb[18 chars]t': 81.17, 'aurora': 80.17, 'cobalt': 80.17, '[109 chars] 0.0}
  {'aurora': 80.17,
-  'basalt': 80.67,
?             ^ ^

+  'basalt': 81.17,
?             ^ ^

   'cobalt': 80.17,
   'dynamo': 60.33,
   'ember': 88.33,
   'garnet': 18.33,
   's-hydra': 68.33,
   's-iris': 72.5,
   's-ja ...
```

### B2: Resubmissions counted as extra tasks

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_2_tasks_attempted: aurora, basalt, s-iris and s-koi show 4 tasks attempted instead of 3.
- **Location:** `podium/scoring.py` → `tasks_attempted`
- **Why it fails:** Collecting tasks in a list keeps one entry per submission, so a team that resubmitted a task counts it twice. Rule 6 counts different tasks.
- **Failing test:** `test_1_scores.TestScores.test_2_tasks_attempted`
- **Unblocks:** test_2_tasks_attempted.

Fix:

```diff
-    seen: dict[str, list] = defaultdict(list)
+    seen: dict[str, set] = defaultdict(set)
     for s in subs:
-        seen[s.team_id].append(s.task)
+        seen[s.team_id].add(s.task)
```

Observed with only this bug applied (`tests.test_1_scores.TestScores.test_2_tasks_attempted`):

```
AssertionError: {'ember': 3, 'basalt': 4, 'aurora': 4, 'cob[95 chars]': 0} != {'aurora': 3, 'basalt': 3, 'cobalt': 3, 'dy[95 chars]': 0}
- {'aurora': 4,
?            ^

+ {'aurora': 3,
?            ^

-  'basalt': 4,
?            ^

+  'basalt': 3,
?            ^

   'cobalt': 3,
   'dynamo': 2,
   'ember': 3,
   'garnet': 1,
   's-hydra': 3,
-  's-iris': 4,
?            ^

+  's-iris': 3,
?       ...
```

### B3: Submission at the freeze dropped

- **Type:** time-window-boundary
- **Symptom:** Test 2 test_3_submission_counts: counted_submissions is 30 instead of 31 (mmlu 10 instead of 11). Scores and ranks are unchanged.
- **Location:** `podium/loader.py` → `load_submissions`
- **Why it fails:** Rule 3 keeps a submission made exactly at the freeze. `>=` drops s-koi's 23:59 mmlu run. It was lower than s-koi's earlier mmlu score, so only the counts notice.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_3_submission_counts`
- **Unblocks:** test_3_submission_counts.

Fix:

```diff
-            if submitted >= FREEZE:
+            if submitted > FREEZE:
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_3_submission_counts`):

```
AssertionError: 30 != 31
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `podium/ranking.py` → `competition_ranks`: Comparing each row with the previous one and reusing the previous rank gives shared ranks for ties, and `i + 1` for the next distinct score skips the right number of places (aurora and cobalt are both 3, s-iris is 5). It looks as if it should count distinct scores, but that would be dense ranking, which the spec does not ask for.
