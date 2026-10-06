# set-035 answer key: Pairwise preferences: win rates, Elo and leaderboard

**Domain:** rlhf_preferences  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_win_rates.TestWinRates.test_win_rates` | B1 Counter.update on a model name counts its letters |
| `test_2_elo.TestElo.test_elo_ratings` | B2 Round kept as text, so 10-12 sort before 2 |
| `test_2_elo.TestElo.test_leaderboard` | B3 Model with exactly the minimum games left off |

## Failing pattern with all bugs present

- `tests.test_1_win_rates.TestWinRates.test_win_rates`
- `tests.test_2_elo.TestElo.test_elo_ratings`
- `tests.test_2_elo.TestElo.test_leaderboard`

## Bugs (recommended order)

### B1: Counter.update on a model name counts its letters

- **Type:** counter-misuse
- **Symptom:** Test 1 test_win_rates: every rate collapses to the tie credit only, e.g. m-alpha 0.042, m-beta 0.077, m-gamma 0.045 (should be 0.875 / 0.692 / 0.5). Games and exclusions are correct.
- **Location:** `prefrank/stats.py` → `win_rates`
- **Why it fails:** Counter.update iterates its argument, and iterating a string yields its characters, so the counts go to 'm', '-', 'a', … and no model ever has a win. Only the half-credit from ties is left.
- **Failing test:** `test_1_win_rates.TestWinRates.test_win_rates`
- **Unblocks:** test_win_rates.

Fix:

```diff
-            wins.update(comp.winner)
+            wins[comp.winner] += 1
```

Observed with only this bug applied (`tests.test_1_win_rates.TestWinRates.test_win_rates`):

```
AssertionError: {'m-alpha': 0.042, 'm-beta': 0.077, 'm-delta': 0.042, '[26 chars].045} != {'m-alpha': 0.875, 'm-beta': 0.692, 'm-delta': 0.125, '[24 chars] 0.5}
- {'m-alpha': 0.042,
?               ^^^

+ {'m-alpha': 0.875,
?               ^^^

-  'm-beta': 0.077,
?              ^^^

+  'm-beta': 0.692,
?              ^^^

-  'm-delta': 0.042,
?               ^^

+  'm-delta': 0.125,
?             ...
```

### B2: Round kept as text, so 10-12 sort before 2

- **Type:** string-vs-int
- **Symptom:** Test 2 test_elo_ratings: all ratings shift slightly, e.g. m-alpha 1107.4 vs 1118.7, m-beta 1075.9 vs 1062.0, m-gamma 994.9 vs 1000.4. The sum and the leaderboard order are unchanged.
- **Location:** `prefrank/loader.py` → `load_comparisons`
- **Why it fails:** elo_ratings sorts by `round`. As strings, '10', '11', '12' sort between '1' and '2', so rounds 10-12 are applied early. Elo is order-dependent, so every rating shifts slightly, though win rates and the leaderboard order don't change.
- **Failing test:** `test_2_elo.TestElo.test_elo_ratings`
- **Unblocks:** test_elo_ratings.

Fix:

```diff
-                valid.append(Comparison(clean(row["comparison_id"]).lower(), clean(row["round"]),
+                valid.append(Comparison(clean(row["comparison_id"]).lower(), int(clean(row["round"])),
```

Observed with only this bug applied (`tests.test_2_elo.TestElo.test_elo_ratings`):

```
AssertionError: {'m-alpha': 1107.4, 'm-beta': 1075.9, 'm-delta': 884.1,[29 chars]94.9} != {'m-alpha': 1118.7, 'm-beta': 1062.0, 'm-delta': 883.1,[30 chars]00.4}
- {'m-alpha': 1107.4,
?               ^ --

+ {'m-alpha': 1118.7,
?               ^^^

-  'm-beta': 1075.9,
?              ^^ ^

+  'm-beta': 1062.0,
?              ^^ ^

-  'm-delta': 884.1,
?               ^

+  'm-delta': 883.1,
?       ...
```

### B3: Model with exactly the minimum games left off

- **Type:** off-by-one
- **Symptom:** Test 2 test_leaderboard: [m-alpha, m-beta, m-delta]; m-gamma (exactly 11 games) is missing.
- **Location:** `prefrank/reports.py` → `leaderboard`
- **Why it fails:** The README says at least 11 games. m-gamma has exactly 11 and `>` drops it.
- **Failing test:** `test_2_elo.TestElo.test_leaderboard`
- **Unblocks:** test_leaderboard.

Fix:

```diff
-    eligible = [m for m in ratings if games[m] > MIN_GAMES]
+    eligible = [m for m in ratings if games[m] >= MIN_GAMES]
```

Observed with only this bug applied (`tests.test_2_elo.TestElo.test_leaderboard`):

```
AssertionError: Lists differ: ['m-alpha', 'm-beta', 'm-delta'] != ['m-alpha', 'm-beta', 'm-gamma', 'm-delta']

First differing element 2:
'm-delta'
'm-gamma'

Second list contains 1 additional elements.
First extra element 3:
'm-delta'

- ['m-alpha', 'm-beta', 'm-delta']
+ ['m-alpha', 'm-beta', 'm-gamma', 'm-delta']
?                      +++++++++++
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `prefrank/elo.py` → `expected_score`: `opponent - rating` in the exponent looks reversed, but it is the standard Elo formula from README rule 8: a stronger opponent makes the exponent positive and the expected score drop below 0.5.
