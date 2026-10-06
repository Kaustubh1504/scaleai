# set-089 answer key: Eval Cup leaderboard with a contest window

**Domain:** leaderboard_ranking  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_scores.TestScores.test_1_mid_table_composites` | B1 Submission at the window end counted |
| `test_2_leaderboard.TestLeaderboard.test_2_final_standings` | B2 Tie-break uses first submission time |
| `test_2_leaderboard.TestLeaderboard.test_3_benchmark_stats` | B3 Entrant count counts submissions, not teams |

## Failing pattern with all bugs present

- `tests.test_1_scores.TestScores.test_1_mid_table_composites`
- `tests.test_2_leaderboard.TestLeaderboard.test_2_final_standings`
- `tests.test_2_leaderboard.TestLeaderboard.test_3_benchmark_stats`

## Bugs (recommended order)

### B1: Submission at the window end counted

- **Type:** time-window-boundary
- **Symptom:** test_1_mid_table_composites fails: orca shows (0.7167, 52.0) instead of (0.7, 48.0). puffin and otter are unchanged and the standings test still passes.
- **Location:** `evalboard/loader.py` → `in_window`
- **Why it fails:** The window is end-exclusive. With `<=`, orca's S24 (exactly 2026-09-15 00:00, written as 09/15/2026 00:00) counts, so orca's reasoning best rises from 48 to 52 and its composite from 0.7 to 0.7167. It is not enough to change orca's rank.
- **Failing test:** `test_1_scores.TestScores.test_1_mid_table_composites`
- **Unblocks:** test_1_mid_table_composites.

Fix:

```diff
-    return start <= ts <= end
+    return start <= ts < end
```

Observed with only this bug applied (`tests.test_1_scores.TestScores.test_1_mid_table_composites`):

```
AssertionError: {'puffin': (0.75, 60.0), 'otter': (0.7333, 72.0), 'orca': (0.7167, 52.0)} != {'puffin': (0.75, 60.0), 'otter': (0.7333, 72.0), 'orca': (0.7, 48.0)}
- {'orca': (0.7167, 52.0), 'otter': (0.7333, 72.0), 'puffin': (0.75, 60.0)}
?              ---  ^^

+ {'orca': (0.7, 48.0), 'otter': (0.7333, 72.0), 'puffin': (0.75, 60.0)}
?                ^^
```

### B2: Tie-break uses first submission time

- **Type:** wrong-tie-break
- **Symptom:** test_2_final_standings fails: heron is ranked 6th and lynx 7th. Expected lynx then heron (both have composite 0.6667).
- **Location:** `evalboard/scoring.py` → `team_bests`
- **Why it fails:** lynx and heron have identical bests and composites (0.6667). The tie goes to whoever made their last submission earlier (lynx, 09-10 vs heron 09-12). `min` gives each team's first submission instead, and heron started earlier (09-02), so the two swap.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_2_final_standings`
- **Unblocks:** test_2_final_standings.

Fix:

```diff
-    last_seen = {team: min(ts) for team, ts in times.items()}
+    last_seen = {team: max(ts) for team, ts in times.items()}
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_2_final_standings`):

```
AssertionError: Lists differ: ['kel[13 chars], 'puffin', 'otter', 'orca', 'heron', 'lynx', 'wren', 'marten'] != ['kel[13 chars], 'puffin', 'otter', 'orca', 'lynx', 'heron', 'wren', 'marten']

First differing element 5:
'heron'
'lynx'

  ['kelp',
   'narwhal',
   'puffin',
   'otter',
   'orca',
+  'lynx',
   'heron',
-  'lynx',
   'wren',
   'marten']
```

### B3: Entrant count counts submissions, not teams

- **Type:** missing-dedupe
- **Symptom:** test_3_benchmark_stats fails: latency_ms teams is 8 (expected 7) and reasoning teams is 9 (expected 8). coding and safety are right.
- **Location:** `evalboard/report.py` → `benchmark_stats`
- **Why it fails:** `teams` must count distinct teams. A list keeps one entry per submission, so kelp's two reasoning and two latency submissions are counted twice. coding and safety happen to be right because nobody submitted to them twice.
- **Failing test:** `test_2_leaderboard.TestLeaderboard.test_3_benchmark_stats`
- **Unblocks:** test_3_benchmark_stats.

Fix:

```diff
-    entrants = defaultdict(list)
+    entrants = defaultdict(set)
     for sub in submissions:
         if sub.benchmark in benchmarks:
-            entrants[sub.benchmark].append(sub.team)
+            entrants[sub.benchmark].add(sub.team)
```

Observed with only this bug applied (`tests.test_2_leaderboard.TestLeaderboard.test_3_benchmark_stats`):

```
AssertionError: {'cod[73 chars]ms': 8, 'leader': 'kelp', 'best': 200.0}, 'rea[109 chars]0.0}} != {'cod[73 chars]ms': 7, 'leader': 'kelp', 'best': 200.0}, 'rea[109 chars]0.0}}
  {'coding': {'best': 50.0, 'leader': 'puffin', 'teams': 8},
-  'latency_ms': {'best': 200.0, 'leader': 'kelp', 'teams': 8},
?                                                           ^

+  'latency_ms': {'best': 200.0, 'lea ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `evalboard/loader.py` → `parse_time`: It tries exactly the three formats the README lists, with month/day order for the slash format, and raises on anything else. The `continue` inside `except` only moves on to the next format.
- `evalboard/scoring.py` → `normalise`: For a lower-is-better benchmark the leader has the smallest value, so `best / score` puts the leader at 1.0 and every slower team below 1. It looks inverted, but it is exactly spec rule 6.
