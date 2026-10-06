# set-094 answer key: Moderation HITL router: thresholds, legacy models, reviewer pools, calibration

**Domain:** hitl_routing  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_routing.TestRouting.test_guard_mini_routing` | B1 Threshold 0.0 replaced by the default |
| `test_1_routing.TestRouting.test_legacy_model_routing` | B2 Legacy-model check compares an Enum to a string |
| `test_2_assignment.TestAssignment.test_spanish_pool` | B3 and/or precedence lets any senior take any item |
| `test_2_assignment.TestAssignment.test_english_pool` | B4 Reviewer pool not lower-cased |
| `test_3_calibration.TestCalibration.test_label_confusions` | B5 Confusion ties broken by insertion order |
| `test_3_calibration.TestCalibration.test_model_calibration` | B6 groupby over unsorted reviews |

## Failing pattern with all bugs present

- `tests.test_1_routing.TestRouting.test_guard_mini_routing`
- `tests.test_1_routing.TestRouting.test_legacy_model_routing`
- `tests.test_2_assignment.TestAssignment.test_english_pool`
- `tests.test_2_assignment.TestAssignment.test_spanish_pool`
- `tests.test_3_calibration.TestCalibration.test_label_confusions`
- `tests.test_3_calibration.TestCalibration.test_model_calibration`

## Bugs (recommended order)

### B1: Threshold 0.0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 1 test_guard_mini_routing: M01 (0.35) and M03 (61%) come out ('crowd', 'low_confidence') instead of ('auto', 'confident'). M02 (0.92) is still auto. Nothing downstream changes, because severity-1 fallbacks go to crowd.
- **Location:** `hitlroute/policy.py` → `Policy.threshold_for`
- **Why it fails:** promo has threshold 0.0, which is falsy, so `or` swaps in the 0.8 default. Promo predictions below 0.8 then fail rule 5 and fall back to crowd.
- **Failing test:** `test_1_routing.TestRouting.test_guard_mini_routing`
- **Unblocks:** test_guard_mini_routing.

Fix:

```diff
-        return rule.threshold or self.default_threshold
+        return rule.threshold if rule.threshold is not None else self.default_threshold
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_guard_mini_routing`):

```
AssertionError: {'M01': ('crowd', 'low_confidence'), 'M02': ('auto'[171 chars]ed')} != {'M01': ('auto', 'confident'), 'M02': ('auto', 'con[159 chars]ed')}
- {'M01': ('crowd', 'low_confidence'),
?           ^^ --    ----        ^^

+ {'M01': ('auto', 'confident'),
?           ^^^             ^

   'M02': ('auto', 'confident'),
-  'M03': ('crowd', 'low_confidence'),
?           ^^ --    ----         ...
```

### B2: Legacy-model check compares an Enum to a string

- **Type:** enum-vs-string
- **Symptom:** Test 1 test_legacy_model_routing: L01, L02 and L04 from legacy guard-v1 come out ('auto', 'confident') instead of ('crowd', 'legacy_model').
- **Location:** `hitlroute/router.py` → `decide`
- **Why it fails:** route is a Route member. Route is a plain Enum, not a str subclass, so Route.AUTO == "auto" is False and the legacy override never runs. guard-v1 predictions with high confidence are auto-accepted.
- **Failing test:** `test_1_routing.TestRouting.test_legacy_model_routing`
- **Unblocks:** test_legacy_model_routing.

Fix:

```diff
-    if route == "auto" and pred.model in policy.legacy_models:
+    if route is Route.AUTO and pred.model in policy.legacy_models:
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_legacy_model_routing`):

```
AssertionError: {'L01': ('auto', 'confident'), 'L02': ('auto', 'con[107 chars]ce')} != {'L01': ('crowd', 'legacy_model'), 'L02': ('crowd',[119 chars]ce')}
- {'L01': ('auto', 'confident'),
-  'L02': ('auto', 'confident'),
+ {'L01': ('crowd', 'legacy_model'),
+  'L02': ('crowd', 'legacy_model'),
   'L03': ('expert', 'low_confidence'),
-  'L04': ('auto', 'confident'),
+  'L04': ('crowd', 'legacy_mode ...
```

### B3: and/or precedence lets any senior take any item

- **Type:** or-precedence
- **Symptom:** Test 2 test_spanish_pool: inactive reviewer rv-06 is given I04 and I20, rv-07 only gets I12, and the es backlog is empty instead of ['I20'].
- **Location:** `hitlroute/assign.py` → `eligible`
- **Why it fails:** Without the parentheses, `and` binds tighter, so the test reads `(active and has room and severity < 5) or senior`. Any senior counts as eligible, even an inactive one or one at capacity. Inactive senior rv-06 has the fewest items, so they pick up the Spanish queue.
- **Failing test:** `test_2_assignment.TestAssignment.test_spanish_pool`
- **Unblocks:** test_spanish_pool.

Fix:

```diff
-    return reviewer.active and reviewer.load < reviewer.capacity and severity < SENIOR_ONLY_SEVERITY or reviewer.senior
+    return reviewer.active and reviewer.load < reviewer.capacity and (severity < SENIOR_ONLY_SEVERITY or reviewer.senior)
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_spanish_pool`):

```
AssertionError: Tuples differ: ({'rv-05': ['I05', 'I18'], 'rv-06': ['I04', 'I20'], 'rv-07': ['I12']}, []) != ({'rv-05': ['I05', 'I12'], 'rv-06': [], 'rv-07': ['I04', 'I18']}, ['I20'])

First differing element 0:
{'rv-05': ['I05', 'I18'], 'rv-06': ['I04', 'I20'], 'rv-07': ['I12']}
{'rv-05': ['I05', 'I12'], 'rv-06': [], 'rv-07': ['I04', 'I18']}

- ({'rv-05': ['I05', 'I18'], 'rv-06': ['I04', 'I20'],  ...
```

### B4: Reviewer pool not lower-cased

- **Type:** id-normalization
- **Symptom:** Test 2 test_english_pool: rv-02 gets nothing, rv-01 gets ['I03', 'L03', 'I14'], rv-03 gets ['I02', 'I11'], and I19 goes to the en backlog.
- **Location:** `hitlroute/loader.py` → `load_reviewers`
- **Why it fails:** rv-02's pool is ' EN'. Trimmed but not lower-cased it becomes 'EN', which never equals the item language 'en'. The English pool loses a reviewer, the others take on more, and I19 lands in the backlog.
- **Failing test:** `test_2_assignment.TestAssignment.test_english_pool`
- **Unblocks:** test_english_pool.

Fix:

```diff
-            pool=clean(row["pool"]),
+            pool=clean(row["pool"]).lower(),
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_english_pool`):

```
AssertionError: Tuples differ: ({'rv-01': ['I03', 'L03', 'I14'], 'rv-02': [], 'rv-03': ['I02[28 chars]19']) != ({'rv-01': ['I03', 'I11'], 'rv-02': ['I02', 'I14'], 'rv-03': [28 chars], [])

First differing element 0:
{'rv-01': ['I03', 'L03', 'I14'], 'rv-02': [], 'rv-03': ['I02[18 chars]: []}
{'rv-01': ['I03', 'I11'], 'rv-02': ['I02', 'I14'], 'rv-03': [23 chars]: []}

- ({'rv-01': ['I03', 'L03', 'I1 ...
```

### B5: Confusion ties broken by insertion order

- **Type:** wrong-tie-break
- **Symptom:** Test 3 test_label_confusions: promo → 'spam' (should be 'off_topic') and spam → 'promo' (should be 'low_quality'). Every other label is right.
- **Location:** `hitlroute/calibration.py` → `label_confusions`
- **Why it fails:** most_common breaks ties by first insertion, so whichever human label appeared first in reviews.csv wins. The spec breaks ties alphabetically. promo (spam vs off_topic) and spam (promo vs low_quality) are both 1-1 ties.
- **Failing test:** `test_3_calibration.TestCalibration.test_label_confusions`
- **Unblocks:** test_label_confusions.

Fix:

```diff
-        result[label] = counts.most_common(1)[0][0] if counts else None
+        result[label] = min(counts, key=lambda h: (-counts[h], h)) if counts else None
```

Observed with only this bug applied (`tests.test_3_calibration.TestCalibration.test_label_confusions`):

```
AssertionError: {'adu[107 chars]'off_topic': None, 'promo': 'spam', 'spam': 'promo'} != {'adu[107 chars]'off_topic': None, 'promo': 'off_topic', 'spam': 'low_quality'}
  {'adult': 'clean',
   'clean': None,
   'graphic_violence': None,
   'harassment': 'clean',
   'hate_speech': 'harassment',
   'off_topic': None,
-  'promo': 'spam',
-  'spam': 'promo'}
+  'promo': 'off_topic',
+  'spam': 'low_qua ...
```

### B6: groupby over unsorted reviews

- **Type:** groupby-misuse
- **Symptom:** Test 3 test_model_calibration: each model's stats come from only its last run of consecutive rows, e.g. guard-mini shows reviews 1, agreement 1.0 instead of 6 / 0.667. test_models_listed still passes.
- **Location:** `hitlroute/calibration.py` → `model_calibration`
- **Why it fails:** itertools.groupby only groups consecutive rows. reviews.csv alternates models, so each model shows up as many short runs, and each run overwrites the table entry. Only the last run of each model survives.
- **Failing test:** `test_3_calibration.TestCalibration.test_model_calibration`
- **Unblocks:** test_model_calibration.

Fix:

```diff
-    for model, group in groupby(reviews, key=_model):
+    for model, group in groupby(sorted(reviews, key=_model), key=_model):
```

Observed with only this bug applied (`tests.test_3_calibration.TestCalibration.test_model_calibration`):

```
AssertionError: {'gua[17 chars]ws': 1, 'agreement': 1.0, 'mean_confidence': 0[182 chars].08}} != {'gua[17 chars]ws': 6, 'agreement': 0.667, 'mean_confidence':[189 chars]236}}
Diff is 1220 characters long. Set self.maxDiff to None to see it.
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `hitlroute/assign.py` → `queue_order`: The minus on severity looks like a flipped sort, but 5 is the most severe, so ascending on -severity handles severity 5 first. Then earliest received_at, then item_id, exactly as rule 9 says.
- `hitlroute/loader.py` → `parse_confidence`: The comma replace and the percent branch look like guesswork, but the README lists exactly these formats: '0,90' and '88%' must come out as 0.9 and 0.88. Blank returns None, which the router treats as no_confidence.
