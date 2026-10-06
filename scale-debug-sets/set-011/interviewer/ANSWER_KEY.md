# set-011 answer key: Pairwise preference win rates and Elo leaderboard

**Domain:** rlhf_preferences  |  **Length:** MINI  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_ratings.TestRatings.test_1_win_rates` | B1 both_bad counted as a tie |
| `test_1_ratings.TestRatings.test_2_elo_ratings` | B2 Ratings rounded to whole numbers on every update |
| `test_2_leaderboard.TestLeaderboard.test_3_leaderboard` | B3 Model with exactly 4 games left off the leaderboard |

## Failing pattern with all bugs present

- `tests.test_1_ratings.TestRatings.test_1_win_rates`
- `tests.test_1_ratings.TestRatings.test_2_elo_ratings`
- `tests.test_2_leaderboard.TestLeaderboard.test_3_leaderboard`

## Bugs (recommended order)

### B1: both_bad counted as a tie

- **Type:** or-precedence
- **Symptom:** test_1_win_rates fails: ties are too high for every model that played a both_bad game (atlas 4 instead of 3, borealis 3 instead of 1, cirrus 3 instead of 1, ember 2 instead of 1), so win rates rise (cirrus 0.85, borealis 0.278, ember 0.5). delta-3b is unchanged.
- **Location:** `prefrank/winrates.py` → `win_table`
- **Why it fails:** `c.winner == "tie" or "draw"` parses as `(c.winner == "tie") or "draw"`, and the non-empty string is always truthy. Every row that is not a/b, including both_bad, lands in the tie branch.
- **Failing test:** `test_1_ratings.TestRatings.test_1_win_rates`
- **Unblocks:** test_1_win_rates.

Fix:

```diff
-        elif c.winner == "tie" or "draw":
+        elif c.winner == "tie" or c.winner == "draw":
```

Observed with only this bug applied (`tests.test_1_ratings.TestRatings.test_1_win_rates`):

```
AssertionError: {'atlas-7b': (2, 4, 0.4), 'borealis-13b': (1, 3, 0.278), '[75 chars]0.5)} != {'atlas-7b': (2, 3, 0.35), 'borealis-13b': (1, 1, 0.167), [78 chars]375)}
- {'atlas-7b': (2, 4, 0.4),
?                  ^    ^

+ {'atlas-7b': (2, 3, 0.35),
?                  ^    ^^

-  'borealis-13b': (1, 3, 0.278),
?                      ^    ^ -

+  'borealis-13b': (1, 1, 0.167),
?                    ...
```

### B2: Ratings rounded to whole numbers on every update

- **Type:** float-rounding
- **Symptom:** test_2_elo_ratings fails: every rating is a whole number (atlas 969, cirrus 1094, ember 1000) and borealis has drifted to 951 instead of 949.3.
- **Location:** `prefrank/elo.py` → `update`
- **Why it fails:** The spec keeps full precision during the updates and rounds only in the report. Rounding to integers after every game throws away the fractional part each step, and the error builds up across the sequence.
- **Failing test:** `test_1_ratings.TestRatings.test_2_elo_ratings`
- **Unblocks:** test_2_elo_ratings.

Fix:

```diff
-    return round(ra + delta), round(rb - delta)
+    return ra + delta, rb - delta
```

Observed with only this bug applied (`tests.test_1_ratings.TestRatings.test_2_elo_ratings`):

```
AssertionError: {'atlas-7b': 969, 'borealis-13b': 951, 'cirrus-70b': 1094[33 chars]1000} != {'atlas-7b': 969.6, 'borealis-13b': 949.3, 'cirrus-70b': [43 chars]00.7}
- {'atlas-7b': 969,
+ {'atlas-7b': 969.6,
?                 ++

-  'borealis-13b': 951,
?                   ^^

+  'borealis-13b': 949.3,
?                   ^^^^

-  'cirrus-70b': 1094,
+  'cirrus-70b': 1094.2,
?                    ++ ...
```

### B3: Model with exactly 4 games left off the leaderboard

- **Type:** off-by-one
- **Symptom:** test_3_leaderboard fails: the leaderboard is ['cirrus-70b', 'atlas-7b', 'borealis-13b']; ember-8x7b (exactly 4 games) is missing.
- **Location:** `prefrank/reports.py` → `leaderboard`
- **Why it fails:** The spec says at least 4 games. `>` needs 5 or more, so ember-8x7b, which has exactly 4, is dropped.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_3_leaderboard`
- **Unblocks:** test_3_leaderboard.

Fix:

```diff
-stats.games > MIN_GAMES]
+stats.games >= MIN_GAMES]
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_3_leaderboard`):

```
AssertionError: Lists differ: ['cirrus-70b', 'atlas-7b', 'borealis-13b'] != ['cirrus-70b', 'ember-8x7b', 'atlas-7b', 'borealis-13b']

First differing element 1:
'atlas-7b'
'ember-8x7b'

Second list contains 1 additional elements.
First extra element 3:
'borealis-13b'

- ['cirrus-70b', 'atlas-7b', 'borealis-13b']
+ ['cirrus-70b', 'ember-8x7b', 'atlas-7b', 'borealis-13b']
?                ++++++++++ ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `prefrank/elo.py` → `expected_score`: The `(opponent - rating)` order looks reversed, but it is exactly the spec's 1 / (1 + 10^((R_B - R_A)/400)): a higher own rating makes the exponent negative and the expected score larger.
- `prefrank/loader.py` → `parse_rated_at`: It covers exactly the three timestamp formats the README lists, with month/day order for the slash format.
