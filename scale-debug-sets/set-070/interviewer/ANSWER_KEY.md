# set-070 answer key: Confidence routing to human review: flags, worklist urgency, run summary

**Domain:** hitl_routing  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_routing.TestRouting.test_toxicity_review_reasons` | B1 Zero confidence treated as missing |
| `test_1_routing.TestRouting.test_caption_review_reasons` | B2 Sensitive flag parsed with bool() |
| `test_2_worklists.TestWorklists.test_mixed_priority_worklists` | B3 Priority sorted as if higher is more urgent |
| `test_2_worklists.TestWorklists.test_equal_confidence_worklist` | B4 Equal-urgency tie broken by item id |
| `test_3_report.TestReport.test_auto_accept_rate` | B5 Decision compared with a plain string |
| `test_3_report.TestReport.test_mean_review_confidence` | B6 Mean confidence over all items |

## Failing pattern with all bugs present

- `tests.test_1_routing.TestRouting.test_caption_review_reasons`
- `tests.test_1_routing.TestRouting.test_toxicity_review_reasons`
- `tests.test_2_worklists.TestWorklists.test_equal_confidence_worklist`
- `tests.test_2_worklists.TestWorklists.test_mixed_priority_worklists`
- `tests.test_3_report.TestReport.test_auto_accept_rate`
- `tests.test_3_report.TestReport.test_mean_review_confidence`

## Bugs (recommended order)

### B1: Zero confidence treated as missing

- **Type:** falsy-zero
- **Symptom:** Test 1 test_toxicity_review_reasons: T04 (confidence 0) has reason no_confidence instead of low_confidence. Its decision is still human_review.
- **Location:** `hitlroute/router.py` → `route`
- **Why it fails:** `not 0.0` is True, so T04's genuine confidence of 0 is reported as no_confidence. The README says 0 is a real confidence, which makes T04 low_confidence.
- **Failing test:** `test_1_routing.TestRouting.test_toxicity_review_reasons`
- **Unblocks:** test_toxicity_review_reasons.

Fix:

```diff
-    if not pred.confidence:
+    if pred.confidence is None:
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_toxicity_review_reasons`):

```
AssertionError: {'T02[47 chars]4': 'no_confidence', 'T06': 'no_confidence', '[63 chars]nce'} != {'T02[47 chars]4': 'low_confidence', 'T06': 'no_confidence', [64 chars]nce'}
  {'T02': 'low_confidence',
   'T03': 'label_policy',
-  'T04': 'no_confidence',
?          ^

+  'T04': 'low_confidence',
?          ^ +

   'T06': 'no_confidence',
   'T08': 'sensitive',
   'T09': 'low_confidence',
   'T10':  ...
```

### B2: Sensitive flag parsed with bool()

- **Type:** bool-from-string
- **Symptom:** Test 1 test_caption_review_reasons: C02 ('no'), C03 ('false') and C06 ('N') have reason sensitive instead of low_confidence. Decisions are unchanged.
- **Location:** `hitlroute/loader.py` → `parse_flag`
- **Why it fails:** parse_flag returns bool() of the trimmed text, and any non-empty string is True, so 'no', 'false' and 'N' all count as sensitive. C02, C03 and C06 get reason sensitive instead of low_confidence. Their decision is review either way, so only the reason changes.
- **Failing test:** `test_1_routing.TestRouting.test_caption_review_reasons`
- **Unblocks:** test_caption_review_reasons.

Fix:

```diff
-    return bool(clean(value))
+    return clean(value).lower() in {"yes", "y", "true", "1"}
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_caption_review_reasons`):

```
AssertionError: {'C02': 'sensitive', 'C03': 'sensitive', 'C05': 'l[100 chars]nce'} != {'C02': 'low_confidence', 'C03': 'low_confidence',[115 chars]nce'}
- {'C02': 'sensitive',
-  'C03': 'sensitive',
+ {'C02': 'low_confidence',
+  'C03': 'low_confidence',
   'C05': 'low_confidence',
-  'C06': 'sensitive',
+  'C06': 'low_confidence',
   'C07': 'sensitive',
   'C08': 'low_confidence',
   'C09': 'low_ ...
```

### B3: Priority sorted as if higher is more urgent

- **Type:** sort-direction
- **Symptom:** Test 2 test_mixed_priority_worklists: r01 is ['P08', 'P02', 'T06', 'P05'] instead of ['T06', 'P05', 'P08', 'P02'], and r05 is ['C03', 'C08'] instead of ['C08', 'C03'].
- **Location:** `hitlroute/worklist.py` → `urgency`
- **Why it fails:** This project uses priority 1 = most urgent, so the sort key must be the priority ascending. Negating it puts priority 2/3 items first in mixed worklists (r01, r05).
- **Failing test:** `test_2_worklists.TestWorklists.test_mixed_priority_worklists`
- **Unblocks:** test_mixed_priority_worklists.

Fix:

```diff
-    return (-pred.priority, confidence)
+    return (pred.priority, confidence)
```

Observed with only this bug applied (`tests.test_2_worklists.TestWorklists.test_mixed_priority_worklists`):

```
AssertionError: {'r01': ['P08', 'P02', 'T06', 'P05'], 'r05': ['C03', 'C08']} != {'r01': ['T06', 'P05', 'P08', 'P02'], 'r05': ['C08', 'C03']}
- {'r01': ['P08', 'P02', 'T06', 'P05'], 'r05': ['C03', 'C08']}
+ {'r01': ['T06', 'P05', 'P08', 'P02'], 'r05': ['C08', 'C03']}
```

### B4: Equal-urgency tie broken by item id

- **Type:** wrong-tie-break
- **Symptom:** Test 2 test_equal_confidence_worklist: r10 is ['C06', 'C09'] instead of ['C09', 'C06'].
- **Location:** `hitlroute/worklist.py` → `build_worklists`
- **Why it fails:** The two-pass stable sort means the first pass decides the order of items with equal urgency. Sorting that pass by item_id instead of created_at puts C06 (08:19) before C09 (08:09), although both are priority 3 with confidence 0.69.
- **Failing test:** `test_2_worklists.TestWorklists.test_equal_confidence_worklist`
- **Unblocks:** test_equal_confidence_worklist.

Fix:

```diff
-        items.sort(key=lambda i: i.prediction.item_id)  # oldest first among equals (sort is stable)
+        items.sort(key=lambda i: i.prediction.created_at)  # oldest first among equals (sort is stable)
```

Observed with only this bug applied (`tests.test_2_worklists.TestWorklists.test_equal_confidence_worklist`):

```
AssertionError: Lists differ: ['C06', 'C09'] != ['C09', 'C06']

First differing element 0:
'C06'
'C09'

- ['C06', 'C09']
+ ['C09', 'C06']
```

### B5: Decision compared with a plain string

- **Type:** enum-vs-string
- **Symptom:** Test 3 test_auto_accept_rate: every rate is 0.0 ({'caption': 0.0, 'pii': 0.0, 'toxicity': 0.0}) instead of 0.3 / 0.375 / 0.3.
- **Location:** `hitlroute/reports.py` → `summarize`
- **Why it fails:** Decision is a plain Enum, so Decision.AUTO_ACCEPT never equals the string 'auto_accept'. Nothing is counted and every rate is 0.0.
- **Failing test:** `test_3_report.TestReport.test_auto_accept_rate`
- **Unblocks:** test_auto_accept_rate.

Fix:

```diff
-    auto = Counter(r.prediction.task for r in routed if r.decision == "auto_accept")
+    auto = Counter(r.prediction.task for r in routed if r.decision is Decision.AUTO_ACCEPT)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_auto_accept_rate`):

```
AssertionError: {'caption': 0.0, 'pii': 0.0, 'toxicity': 0.0} != {'caption': 0.3, 'pii': 0.375, 'toxicity': 0.3}
- {'caption': 0.0, 'pii': 0.0, 'toxicity': 0.0}
?               ^           ^                ^

+ {'caption': 0.3, 'pii': 0.375, 'toxicity': 0.3}
?               ^           ^^^                ^
```

### B6: Mean confidence over all items

- **Type:** counting-wrong-subset
- **Symptom:** Test 3 test_mean_review_confidence: 0.721 instead of 0.644.
- **Location:** `hitlroute/reports.py` → `summarize`
- **Why it fails:** The mean should cover review items only, but iterating over `routed` also includes the nine confident auto-accepted predictions, which pulls the mean up.
- **Failing test:** `test_3_report.TestReport.test_mean_review_confidence`
- **Unblocks:** test_mean_review_confidence.

Fix:

```diff
-    scored = [r.prediction.confidence for r in routed if r.prediction.confidence is not None]
+    scored = [r.prediction.confidence for r in review if r.prediction.confidence is not None]
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_mean_review_confidence`):

```
AssertionError: 0.721 != 0.644
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `hitlroute/assign.py` → `assign_reviewers`: It walks review items in item id order, filters to active reviewers with the skill and spare capacity (`load < capacity`), and picks min by (load, reviewer_id). That is exactly the README rule, and loads are shared across tasks as specified. The three toxicity items in the backlog are real: r01, r02 and r05 are full by then.
- `hitlroute/loader.py` → `parse_confidence`: Blank becomes None, '91%' becomes 0.91, and '0' becomes 0.0. `if not text` tests the string before conversion, so a zero confidence is not lost here.
