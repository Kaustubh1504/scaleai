# set-046 answer key: Confidence-threshold routing to a human review desk

**Domain:** hitl_routing  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_routing.TestRouting.test_1_thresholds_for_v2_items` | B1 Threshold cache keyed by label only |
| `test_1_routing.TestRouting.test_2_decisions` | B2 Confidence equal to threshold sent to humans |
| `test_2_assignment.TestAssignment.test_3_english_reviewers` | B3 Queue sorted least urgent first |
| `test_2_assignment.TestAssignment.test_4_german_reviewers` | B4 Capacity 0 replaced by the default |
| `test_3_report.TestReport.test_5_reviewer_mix` | B5 Counter.update fed a string |
| `test_3_report.TestReport.test_6_exported_timestamps` | B6 Datetimes exported with str() |

## Failing pattern with all bugs present

- `tests.test_1_routing.TestRouting.test_1_thresholds_for_v2_items`
- `tests.test_1_routing.TestRouting.test_2_decisions`
- `tests.test_2_assignment.TestAssignment.test_3_english_reviewers`
- `tests.test_2_assignment.TestAssignment.test_4_german_reviewers`
- `tests.test_3_report.TestReport.test_5_reviewer_mix`
- `tests.test_3_report.TestReport.test_6_exported_timestamps`

## Bugs (recommended order)

### B1: Threshold cache keyed by label only

- **Type:** cache-key-missing-param
- **Symptom:** Test 1 test_1_thresholds_for_v2_items: v2 items report v1 thresholds (P-03/P-04/P-11 show 0.8 instead of 0.95, P-06 0.9 instead of 0.92, P-08 0.85 instead of 0.88). Every decision is still the same.
- **Location:** `routedesk/thresholds.py` → `ThresholdTable.lookup`
- **Why it fails:** The memo key drops the model version, so whichever model asks for a label first fixes the threshold for every model. v2 spam items get v1's 0.80 instead of 0.95; the data keeps every decision the same, so only the reported threshold reveals it.
- **Failing test:** `test_1_routing.TestRouting.test_1_thresholds_for_v2_items`
- **Unblocks:** test_1_thresholds_for_v2_items

Fix:

```diff
-        key = label
+        key = (model_version, label)
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_1_thresholds_for_v2_items`):

```
AssertionError: {'P-03': 0.8, 'P-04': 0.8, 'P-06': 0.9, 'P-08': 0.85[49 chars] 0.8} != {'P-03': 0.95, 'P-04': 0.95, 'P-06': 0.92, 'P-08': 0[55 chars]0.95}
- {'P-03': 0.8,
?            ^

+ {'P-03': 0.95,
?            ^^

-  'P-04': 0.8,
?            ^

+  'P-04': 0.95,
?            ^^

-  'P-06': 0.9,
+  'P-06': 0.92,
?             +

-  'P-08': 0.85,
?             ^

+  'P-08': 0.88,
?            ...
```

### B2: Confidence equal to threshold sent to humans

- **Type:** off-by-one
- **Symptom:** Test 1 test_2_decisions: P-07 is routed to 'human' instead of 'auto'. Nothing else changes, because P-07 is Portuguese and no reviewer speaks it.
- **Location:** `routedesk/router.py` → `route_one`
- **Why it fails:** The spec auto-accepts at exactly the threshold. With `>` P-07 (0.75 against the v1 ads threshold 0.75) is routed to a human.
- **Failing test:** `test_1_routing.TestRouting.test_2_decisions`
- **Unblocks:** test_2_decisions

Fix:

```diff
-    if pred.confidence > threshold:
+    if pred.confidence >= threshold:
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_2_decisions`):

```
AssertionError: {'P-0[98 chars]7': 'human', 'P-08': 'auto', 'P-09': 'auto', '[245 chars]man'} != {'P-0[98 chars]7': 'auto', 'P-08': 'auto', 'P-09': 'auto', 'P[244 chars]man'}
  {'P-01': 'auto',
   'P-02': 'human',
   'P-03': 'auto',
   'P-04': 'human',
   'P-05': 'auto',
   'P-06': 'auto',
-  'P-07': 'human',
?           ^ ^^^

+  'P-07': 'auto',
?           ^ ^^

   'P-08': 'auto',
   'P-09': 'au ...
```

### B3: Queue sorted least urgent first

- **Type:** sort-direction
- **Symptom:** Test 2 test_3_english_reviewers: r-01 gets ['P-14', 'P-04'] and r-06 gets ['P-15', 'P-02'] instead of ['P-02', 'P-04'] and ['P-11', 'P-14']. The priority-1 item P-11 ends up unassigned.
- **Location:** `routedesk/assign.py` → `review_queue`
- **Why it fails:** Priority 1 is the most urgent, so it must sort ascending. Negating it hands out priority-3 items first; English capacity runs out and a priority-1 item is left unassigned.
- **Failing test:** `test_2_assignment.TestAssignment.test_3_english_reviewers`
- **Unblocks:** test_3_english_reviewers

Fix:

```diff
-    return sorted(pending, key=lambda p: (-p.priority, p.received_at, p.item_id))
+    return sorted(pending, key=lambda p: (p.priority, p.received_at, p.item_id))
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_3_english_reviewers`):

```
AssertionError: {'r-01': ['P-14', 'P-04'], 'r-03': ['P-26'], 'r-06': ['P-15', 'P-02']} != {'r-01': ['P-02', 'P-04'], 'r-03': ['P-26'], 'r-06': ['P-11', 'P-14']}
- {'r-01': ['P-14', 'P-04'], 'r-03': ['P-26'], 'r-06': ['P-15', 'P-02']}
?              ^^                                           ^      ^^

+ {'r-01': ['P-02', 'P-04'], 'r-03': ['P-26'], 'r-06': ['P-11', 'P-14']}
?              ^^      ...
```

### B4: Capacity 0 replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 2 test_4_german_reviewers: r-07 receives ['P-17'] (expected []), and r-05 takes P-18 instead of P-17.
- **Location:** `routedesk/loader.py` → `load_reviewers`
- **Why it fails:** `0 or DEFAULT_CAPACITY` is 2, so r-07, who is off rotation, receives German items. Only a missing or blank capacity should get the default.
- **Failing test:** `test_2_assignment.TestAssignment.test_4_german_reviewers`
- **Unblocks:** test_4_german_reviewers

Fix:

```diff
-        capacity = int(item.get("capacity") or DEFAULT_CAPACITY)
+        capacity = item.get("capacity")
+        capacity = DEFAULT_CAPACITY if capacity in (None, "") else int(capacity)
```

Observed with only this bug applied (`tests.test_2_assignment.TestAssignment.test_4_german_reviewers`):

```
AssertionError: {'r-05': ['P-10', 'P-16', 'P-18'], 'r-07': ['P-17']} != {'r-05': ['P-10', 'P-16', 'P-17'], 'r-07': []}
- {'r-05': ['P-10', 'P-16', 'P-18'], 'r-07': ['P-17']}
?                               ^             ------

+ {'r-05': ['P-10', 'P-16', 'P-17'], 'r-07': []}
?                               ^
```

### B5: Counter.update fed a string

- **Type:** counter-misuse
- **Symptom:** Test 3 test_5_reviewer_mix: the per-reviewer counts are keyed by single letters, e.g. r-01 → {'a': 3, 'h': 1, 'm': 3, 'p': 2, 's': 2} instead of {'ham': 1, 'spam': 2}.
- **Location:** `routedesk/calibration.py` → `reviewer_mix`
- **Why it fails:** Counter.update iterates its argument, so a bare string counts its characters (`s`, `p`, `a`, `m`) rather than the label.
- **Failing test:** `test_3_report.TestReport.test_5_reviewer_mix`
- **Unblocks:** test_5_reviewer_mix

Fix:

```diff
-        mix[r.reviewer_id].update(r.human_label)
+        mix[r.reviewer_id].update([r.human_label])
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_5_reviewer_mix`):

```
AssertionError: {'r-01': {'a': 3, 'h': 1, 'm': 3, 'p': 2, 's': 2}, '[275 chars]: 1}} != {'r-01': {'ham': 1, 'spam': 2}, 'r-03': {'ok': 1, 't[110 chars]: 1}}
Diff is 664 characters long. Set self.maxDiff to None to see it.
```

### B6: Datetimes exported with str()

- **Type:** json-serialization
- **Symptom:** Test 3 test_6_exported_timestamps: exported last_review_at is '2026-03-01 16:45:00' instead of '2026-03-01T16:45:00' (space instead of T).
- **Location:** `routedesk/reports.py` → `_encode`
- **Why it fails:** `str(datetime)` writes `2026-03-01 16:45:00` (space separator) instead of ISO 8601 `2026-03-01T16:45:00`, which is what the README asks for. json.dumps calls `_encode` for every datetime, so every exported timestamp has the space.
- **Failing test:** `test_3_report.TestReport.test_6_exported_timestamps`
- **Unblocks:** test_6_exported_timestamps

Fix:

```diff
     if isinstance(obj, datetime):
-        return str(obj)
+        return obj.isoformat()
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_6_exported_timestamps`):

```
AssertionError: '2026-03-01 16:45:00' != '2026-03-01T16:45:00'
- 2026-03-01 16:45:00
?           ^
+ 2026-03-01T16:45:00
?           ^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `routedesk/utils.py` → `parse_confidence`: Dividing only when the number is above 1 looks like it mishandles values such as `1%`, but the README defines any value above 1 as a percentage, so `1` is 1.0 and `91`/`91%` are 0.91. Blank values return None as the spec requires.
- `routedesk/loader.py` → `latest_by_item`: The `>=` looks like it should be `>`, but the spec says that on equal timestamps the later row wins. It compares parsed datetimes, so the mixed formats order correctly, and the id is normalised before the lookup so ` P-05`/`p-02` collapse onto their twins.
