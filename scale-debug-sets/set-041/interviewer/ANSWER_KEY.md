# set-041 answer key: Sprint leaderboard with export duplicates and team standings

**Domain:** leaderboard_ranking  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_leaderboard.TestLeaderboard.test_full_rows`
- `tests.test_1_leaderboard.TestLeaderboard.test_order`
- `tests.test_1_leaderboard.TestLeaderboard.test_scores`
- `tests.test_2_teams.TestTeams.test_summary`
- `tests.test_2_teams.TestTeams.test_team_order`
- `tests.test_2_teams.TestTeams.test_team_scores`

## Bugs (recommended order)

### B1: Loop stops at the first banned contributor

- **Type:** early-return
- **Symptom:** Test 1: only 10 contributors ranked, c-01 leads with 21 and c-02 drops to 14, c-03 to 9, c-04 to 12. Test 2: submissions_counted 17 instead of 27, leader c-01, and every team score is low (Falcons 35, Herons 17), so the team order changes too.
- **Location:** `ladder/scoring.py` → `eligible`
- **Why it fails:** `break` ends the whole loop at the first submission from a banned or unknown contributor (S020, Eli), so every later submission in the file is dropped instead of just that one row.
- **Unblocks:** Most of Test 1 and Test 2; it also exposes B2.

Fix:

```diff
         if person is None or person.banned:
-            break
+            continue
```

Observed with only this bug applied (`tests.test_1_leaderboard.TestLeaderboard.test_full_rows`):

```
AssertionError: Lists differ: [{'ra[24 chars]: 'c-01', 'name': 'Ava Brooks', 'score': 21, '[999 chars]: 1}] != [{'ra[24 chars]: 'c-12', 'name': 'Lia Romero', 'score': 23, '[1111 chars]: 1}]

First differing element 0:
{'ran[23 chars]: 'c-01', 'name': 'Ava Brooks', 'score': 21, '[27 chars]': 3}
{'ran[23 chars]: 'c-12', 'name': 'Lia Romero', 'score': 23, '[27 chars]': 3}

Second list contains 1 addi ...
```

### B2: Export duplicates never removed

- **Type:** missing-dedupe
- **Symptom:** Only visible after B1 is fixed. Test 1 test_full_rows: c-12, c-02 and c-03 show 4 attempts instead of 3, and c-02 drops to rank 3 instead of sharing rank 2 with c-01 (scores and order are unchanged). Test 2 test_summary: submissions_counted 30 instead of 27.
- **Location:** `ladder/loader.py` → `load_submissions`
- **Why it fails:** first_per_id is defined but load_submissions returns the raw list, so repeated export rows (s021, S023 , S022) are counted again. Best-per-task scores don't move, but attempts do, which changes the tie-break and the ranks.
- **Unblocks:** Test 1 attempts/order and the Test 2 summary count.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-    return graded
+    return first_per_id(graded)
```

Observed with only this bug applied (`tests.test_1_leaderboard.TestLeaderboard.test_full_rows`):

```
AssertionError: Lists differ: [{'ra[95 chars]ts': 4}, {'rank': 2, 'contributor_id': 'c-01',[1040 chars]: 1}] != [{'ra[95 chars]ts': 3}, {'rank': 2, 'contributor_id': 'c-01',[1040 chars]: 1}]

First differing element 0:
{'ran[38 chars]': 'Lia Romero', 'score': 23, 'tasks_solved': 3, 'attempts': 4}
{'ran[38 chars]': 'Lia Romero', 'score': 23, 'tasks_solved': 3, 'attempts': 3}

- [{'attempts': 4,
?   ...
```

### B3: Team ties ordered reverse-alphabetically

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_team_order only: ['Falcons', 'Otters', 'Herons', 'Lynx'] instead of ['Falcons', 'Herons', 'Otters', 'Lynx']. Scores and Test 1 are unaffected.
- **Location:** `ladder/teams.py` → `team_standings`
- **Why it fails:** Reversing the whole tuple sorts scores high-first correctly but also flips the name tie-break, so Otters (37) lands ahead of Herons (37).
- **Unblocks:** Test 2 team order.
- **Masked:** only surfaces in test_2_teams.

Fix:

```diff
-    table.sort(key=lambda t: (t["score"], t["team"]), reverse=True)
+    table.sort(key=lambda t: (-t["score"], t["team"]))
```

Observed with only this bug applied (`tests.test_2_teams.TestTeams.test_team_order`):

```
AssertionError: Lists differ: ['Falcons', 'Otters', 'Herons', 'Lynx'] != ['Falcons', 'Herons', 'Otters', 'Lynx']

First differing element 1:
'Otters'
'Herons'

- ['Falcons', 'Otters', 'Herons', 'Lynx']
+ ['Falcons', 'Herons', 'Otters', 'Lynx']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `ladder/scoring.py` → `assign_ranks`: `rank = i + 1` looks like it should be `rank += 1`, but standard competition ranking (1, 2, 2, 4) means a new rank is the row's 1-based position, not the previous rank plus one. Rows only share a rank when both score and attempts match, exactly as rule 7 says.
