# set-017 answer key: Labeling challenge leaderboard: best scores and tie-breaks

**Domain:** leaderboard_ranking  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_team_scores.TestTeamScores.test_1_best_scores` | B1 Percentage rounded before scaling |
| `test_1_team_scores.TestTeamScores.test_2_accepted_counts` | B2 Accepted count includes rejected submissions |
| `test_2_leaderboard.TestLeaderboard.test_3_full_leaderboard` | B3 Score ties broken by team id |

## Failing pattern with all bugs present

- `tests.test_1_team_scores.TestTeamScores.test_1_best_scores`
- `tests.test_1_team_scores.TestTeamScores.test_2_accepted_counts`
- `tests.test_2_leaderboard.TestLeaderboard.test_3_full_leaderboard`

## Bugs (recommended order)

### B1: Percentage rounded before scaling

- **Type:** float-rounding
- **Symptom:** test_1_best_scores fails: T02 is 82.89999999999999 instead of 82.9 and T05 is 56.99999999999999 instead of 57.0. Every other test passes, including the leaderboard order.
- **Location:** `podium/scoring.py` → `submission_score`
- **Why it fails:** Rounding the fraction to 3 places and then multiplying by 100 reintroduces binary floating-point error, so 29/35 becomes 82.89999999999999 instead of 82.9. The rounding has to be the last step.
- **Failing test:** `test_1_team_scores.TestTeamScores.test_1_best_scores`
- **Unblocks:** test_1_best_scores.

Fix:

```diff
-    return round(sub.correct / sub.total, 3) * 100
+    return round(100 * sub.correct / sub.total, 1)
```

Observed with only this bug applied (`tests.test_1_team_scores.TestTeamScores.test_1_best_scores`):

```
AssertionError: {'T01[14 chars]: 82.89999999999999, 'T03': 82.5, 'T04': 82.5,[86 chars]37.5} != {'T01[14 chars]: 82.9, 'T03': 82.5, 'T04': 82.5, 'T05': 57.0,[60 chars]37.5}
  {'T01': 85.0,
-  'T02': 82.89999999999999,
+  'T02': 82.9,
   'T03': 82.5,
   'T04': 82.5,
-  'T05': 56.99999999999999,
+  'T05': 57.0,
   'T08': 83.3,
   'T09': 81.8,
   'T10': 73.3,
   'T11': 76.7,
   'T12': 37.5}
```

### B2: Accepted count includes rejected submissions

- **Type:** counting-wrong-subset
- **Symptom:** test_2_accepted_counts fails: T02, T04, T09 and T10 each show one more submission than they should (3, 3, 2, 2 instead of 2, 2, 1, 1).
- **Location:** `podium/scoring.py` → `team_stats`
- **Why it fails:** `subs` is every submission the team made, including rejected ones, while the spec counts only accepted submissions. The filtered list `accepted` is right there.
- **Failing test:** `test_1_team_scores.TestTeamScores.test_2_accepted_counts`
- **Unblocks:** test_2_accepted_counts.

Fix:

```diff
-        stats[team_id] = TeamStats(team_id, submission_score(best), best.submitted_at, len(subs))
+        stats[team_id] = TeamStats(team_id, submission_score(best), best.submitted_at, len(accepted))
```

Observed with only this bug applied (`tests.test_1_team_scores.TestTeamScores.test_2_accepted_counts`):

```
AssertionError: {'T01': 2, 'T02': 3, 'T03': 2, 'T04': 3, 'T05': 2, 'T08': 3[36 chars]': 1} != {'T01': 2, 'T02': 2, 'T03': 2, 'T04': 2, 'T05': 2, 'T08': 3[36 chars]': 1}
  {'T01': 2,
-  'T02': 3,
?         ^

+  'T02': 2,
?         ^

   'T03': 2,
-  'T04': 3,
?         ^

+  'T04': 2,
?         ^

   'T05': 2,
   'T08': 3,
-  'T09': 2,
?         ^

+  'T09': 1,
?         ^

-  'T10': 2,
?          ...
```

### B3: Score ties broken by team id

- **Type:** wrong-tie-break
- **Symptom:** test_3_full_leaderboard fails: positions 4 and 5 are T03 then T04; T04 should be 4th because it reached 82.5 first. Podium and last place are unchanged.
- **Location:** `podium/ranking.py` → `rank`
- **Why it fails:** Without best_at in the key, tied teams fall through to the team id, so T03 lands above T04 even though T04 reached 82.5 a day earlier. The comment still describes the intended rule.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_3_full_leaderboard`
- **Unblocks:** test_3_full_leaderboard.

Fix:

```diff
-    ordered = sorted(stats.values(), key=lambda s: (-s.best_score, s.team_id))
+    ordered = sorted(stats.values(), key=lambda s: (-s.best_score, s.best_at, s.team_id))
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_3_full_leaderboard`):

```
AssertionError: Lists differ: [[1, [34 chars], 'T03'], [5, 'T04'], [6, 'T09'], [7, 'T11'], [31 chars]12']] != [[1, [34 chars], 'T04'], [5, 'T03'], [6, 'T09'], [7, 'T11'], [31 chars]12']]

First differing element 3:
[4, 'T03']
[4, 'T04']

  [[1, 'T01'],
   [2, 'T08'],
   [3, 'T02'],
-  [4, 'T03'],
?         ^

+  [4, 'T04'],
?         ^

-  [5, 'T04'],
?         ^

+  [5, 'T03'],
?         ^

   [6 ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `podium/scoring.py` → `pick_best`: Using min() to find the best looks backwards, but the key negates the score, so the smallest key is the highest score, and ties go to the earliest submitted_at, exactly as rule 2 says.
