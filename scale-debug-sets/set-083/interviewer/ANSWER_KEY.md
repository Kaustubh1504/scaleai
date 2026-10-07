# set-083 answer key: Preference pair builder: screening, margins, standings

**Domain:** rlhf_preferences  |  **Length:** MINI  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_judgements.TestJudgements.test_labeler_quality` | B1 Calibration judgements not deduplicated |
| `test_1_judgements.TestJudgements.test_pair_margins` | B2 left_model compared without normalising |
| `test_2_dataset.TestDataset.test_standings` | B3 reverse=True also reverses the name tie-break |

## Failing pattern with all bugs present

- `tests.test_1_judgements.TestJudgements.test_labeler_quality`
- `tests.test_1_judgements.TestJudgements.test_pair_margins`
- `tests.test_2_dataset.TestDataset.test_standings`

## Bugs (recommended order)

### B1: Calibration judgements not deduplicated

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_labeler_quality: lab-09 shows checks 5, accuracy 0.6, excluded True (expected 4 / 0.75 / False). All verdicts are unchanged, because lab-09 judged no regular pairs.
- **Location:** `prefpairs/reports.py` → `build_report`
- **Why it fails:** Only the regular judgements go through latest_only. lab-09 re-did calibration pair C2, so both the wrong first attempt and the corrected one are counted, 3/5 = 0.6, and lab-09 is excluded.
- **Failing test:** `test_1_judgements.TestJudgements.test_labeler_quality`
- **Unblocks:** test_1 test_labeler_quality.

Fix:

```diff
-    calibration = load_judgements(data_dir / "calibration.csv")
+    calibration = latest_only(load_judgements(data_dir / "calibration.csv"))
```

Observed with only this bug applied (`tests.test_1_judgements.TestJudgements.test_labeler_quality`):

```
AssertionError: {'lab[486 chars], 'lab-09': {'checks': 5, 'accuracy': 0.6, 'excluded': True}} != {'lab[486 chars], 'lab-09': {'checks': 4, 'accuracy': 0.75, 'excluded': False}}
  {'lab-01': {'accuracy': 1.0, 'checks': 2, 'excluded': False},
   'lab-02': {'accuracy': 1.0, 'checks': 2, 'excluded': False},
   'lab-03': {'accuracy': 1.0, 'checks': 2, 'excluded': False},
   'lab-04': {'accuracy': 1.0,  ...
```

### B2: left_model compared without normalising

- **Type:** id-normalization
- **Symptom:** Test 1 test_pair_margins: P08's margin is 0.67 instead of 1.33. Every other margin matches, and P08's verdict is still A.
- **Location:** `prefpairs/aggregate.py` → `margin_of`
- **Why it fails:** Pair models are lower-cased at load, but left_model is only trimmed. j022 has `Cobalt-70b` on the left, so the comparison fails, the judgement is read as if model_b was on the left, and its +1 margin becomes -1.
- **Failing test:** `test_1_judgements.TestJudgements.test_pair_margins`
- **Unblocks:** test_1 test_pair_margins.

Fix:

```diff
# prefpairs/aggregate.py
-    left_is_a = judgement.left_model == pair.model_a
+    left_is_a = norm_model(judgement.left_model) == pair.model_a

# prefpairs/aggregate.py
+from .loader import norm_model
```

Observed with only this bug applied (`tests.test_1_judgements.TestJudgements.test_pair_margins`):

```
AssertionError: {'P01[86 chars]08': 0.67, 'P09': None, 'P10': 1.5, 'P11': 2.5[36 chars]-1.0} != {'P01[86 chars]08': 1.33, 'P09': None, 'P10': 1.5, 'P11': 2.5[36 chars]-1.0}
  {'P01': 1.67,
   'P02': -2.0,
   'P03': 0.0,
   'P04': -1.5,
   'P05': 2.5,
   'P06': 0.5,
   'P07': 0.33,
-  'P08': 0.67,
?         ^ ^^

+  'P08': 1.33,
?         ^ ^^

   'P09': None,
   'P10': 1.5,
   'P11': 2.5,
   'P12' ...
```

### B3: reverse=True also reverses the name tie-break

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_standings: cobalt-70b (0.75) is listed before atlas-7b (0.75); birch-13b and delta-3b are in the right places.
- **Location:** `prefpairs/leaderboard.py` → `standings`
- **Why it fails:** reverse=True flips the whole key tuple, so equal win rates come out in reverse alphabetical order. atlas-7b and cobalt-70b are both 0.75 and swap places.
- **Failing test:** `test_2_dataset.TestDataset.test_standings`
- **Unblocks:** test_2 test_standings.

Fix:

```diff
-    return sorted(rows, key=lambda r: (r["win_rate"], r["model"]), reverse=True)
+    return sorted(rows, key=lambda r: (-r["win_rate"], r["model"]))
```

Observed with only this bug applied (`tests.test_2_dataset.TestDataset.test_standings`):

```
AssertionError: Lists differ: [{'model': 'cobalt-70b', 'wins': 4, 'losses': 1, 'tie[248 chars]0.0}] != [{'model': 'atlas-7b', 'wins': 5, 'losses': 1, 'ties'[248 chars]0.0}]

First differing element 0:
{'model': 'cobalt-70b', 'wins': 4, 'losses': 1, 'ties': 1, 'win_rate': 0.75}
{'model': 'atlas-7b', 'wins': 5, 'losses': 1, 'ties': 2, 'win_rate': 0.75}

+ [{'losses': 1, 'model': 'atlas-7b', 'ties':  ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `prefpairs/aggregate.py` → `a_margin`: The two branches look reversed, but a low rating means the left response won, so 4 - rating is positive exactly when the left (model_a) response is preferred; when model_b was on the left the sign flips.
- `prefpairs/aggregate.py` → `verdict_for`: `abs(margin) < 0.5` matches the spec: only values strictly inside the band are ties, so P06's 0.5 is decided for A.
