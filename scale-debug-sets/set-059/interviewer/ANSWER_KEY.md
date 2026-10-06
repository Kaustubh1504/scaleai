# set-059 answer key: Preference leaderboard: position swaps, Elo, contested prompts

**Domain:** rlhf_preferences  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_ratings.TestRatings.test_comparisons_used`
- `tests.test_1_ratings.TestRatings.test_elo`
- `tests.test_1_ratings.TestRatings.test_win_rates`
- `tests.test_2_leaderboard.TestLeaderboard.test_contested_prompts`
- `tests.test_2_leaderboard.TestLeaderboard.test_leaderboard`

## Bugs (recommended order)

### B1: Comparison rater ids not lower-cased

- **Type:** id-normalization
- **Symptom:** Both files fail. Test 1: used is 18 instead of 22; atlas-7b shows 11 games / 7 wins; Elo becomes borealis 966.8, cirrus-2 987.4, drift-xl 1009.7. Test 2: leaderboard swaps borealis and cirrus-2, and contested is ['p03', 'p04'] (p06 and p10 missing).
- **Location:** `prefrank/loader.py` → `read_comparisons`
- **Why it fails:** The registry ids are lower-cased but comparison rater ids are only trimmed, so every 'R07' row fails the `rater not in qualified` check and is silently dropped.
- **Unblocks:** used, win rates and Elo in Test 1, and p06/p10 in contested. Exposes B2.

Fix:

```diff
-            rater = row["rater"].strip()
+            rater = row["rater"].strip().lower()
```

Observed with only this bug applied (`tests.test_1_ratings.TestRatings.test_comparisons_used`):

```
AssertionError: 18 != 22
```

### B2: swapped = "false" treated as swapped

- **Type:** bool-from-string
- **Symptom:** Only visible after B1 is fixed. Test 1: used stays 22, but atlas-7b shows 9 wins (win_rate 0.731) and Elo shifts (borealis 956.5, cirrus-2 984.6, drift-xl 1004.0). Test 2: leaderboard swaps borealis and cirrus-2, and contested is ['p03', 'p04', 'p08', 'p10'] (p08 instead of p06).
- **Location:** `prefrank/loader.py` → `read_comparisons`
- **Why it fails:** bool() of any non-empty string is True, so R07's rows marked 'false'/'False' get their winner flipped. Blank cells still give False, so only the rater who fills the column is affected.
- **Unblocks:** Test 1 win rates and Elo, and p06 in contested.
- **Masked:** invisible until B1 is fixed (identical test output either way).

Fix:

```diff
-            swapped = bool(row["swapped"].strip())
+            swapped = row["swapped"].strip().lower() in TRUE_WORDS
```

Observed with only this bug applied (`tests.test_1_ratings.TestRatings.test_elo`):

```
AssertionError: {'atlas-7b': 1054.9, 'borealis': 956.5, 'cirrus-2': 984.6, 'drift-xl': 1004.0} != {'atlas-7b': 1030.9, 'borealis': 978.7, 'cirrus-2': 962.5, 'drift-xl': 1028.0}
- {'atlas-7b': 1054.9, 'borealis': 956.5, 'cirrus-2': 984.6, 'drift-xl': 1004.0}
?                ^^                 ^^ ^               ^^ ^                ^^

+ {'atlas-7b': 1030.9, 'borealis': 978.7, 'cirrus-2': 962.5, 'd ...
```

### B3: groupby over unsorted comparisons

- **Type:** groupby-misuse
- **Symptom:** Test 2 test_contested_prompts only: ['p04', 'p10'] instead of ['p03', 'p04', 'p06', 'p10']. Test 1 and the leaderboard pass.
- **Location:** `prefrank/reports.py` → `contested`
- **Why it fails:** itertools.groupby only groups adjacent items. The comparisons are in time order, so p03's and p06's judgements are split by other rows into separate one-item groups and their disagreement is never seen.
- **Unblocks:** test_contested_prompts.
- **Masked:** only surfaces in test_2_leaderboard.

Fix:

```diff
-groupby(comparisons, key=_group_key)
+groupby(sorted(comparisons, key=_group_key), key=_group_key)
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_contested_prompts`):

```
AssertionError: Lists differ: ['p04', 'p10'] != ['p03', 'p04', 'p06', 'p10']

First differing element 0:
'p04'
'p03'

Second list contains 2 additional elements.
First extra element 2:
'p06'

- ['p04', 'p10']
+ ['p03', 'p04', 'p06', 'p10']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `prefrank/ratings.py` → `expected`: The exponent (rb - ra) looks reversed, but when ra > rb it is negative, 10**negative < 1 and the result is above 0.5, so the stronger player is favoured, as the Elo formula in the README says.
