# set-022 answer key: Confidence-threshold triage to a human review queue

**Domain:** hitl_routing  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_routing.TestRouting.test_one_decision_per_prediction`
- `tests.test_1_routing.TestRouting.test_reasons`
- `tests.test_1_routing.TestRouting.test_routes`
- `tests.test_2_review_queue.TestReviewQueue.test_assignments`
- `tests.test_2_review_queue.TestReviewQueue.test_backlog`
- `tests.test_2_review_queue.TestReviewQueue.test_queue_order`
- `tests.test_3_summary.TestSummary.test_backlog_size`
- `tests.test_3_summary.TestSummary.test_busiest_reviewer`
- `tests.test_3_summary.TestSummary.test_by_task_type`

## Bugs (recommended order)

### B1: Dedupe key includes created_at

- **Type:** missing-dedupe
- **Symptom:** Test 1: P003 and P009 appear twice in decisions (26 ids instead of 24), and test_reasons lists stale low_confidence copies of P003 and P009. Test 2: the extra copies enter the queue (P009 right after P018) and shift assignments; backlog becomes P018, P016, P021, P014, P003, P020. Test 3: backlog_size 6, sentiment human 3 / rate 0.5.
- **Location:** `triage/loader.py` → `latest_per_prediction`
- **Why it fails:** With the timestamp in the key, only rows with identical created_at collapse (P016). Re-scores of P003 and P009 at different times both survive, so each gets two decisions and the stale low-confidence copies reach the queue.
- **Unblocks:** test_one_decision_per_prediction and the P003/P009 routes.

Fix:

```diff
-        key = (pred.pred_id, pred.created_at)
+        key = pred.pred_id
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_one_decision_per_prediction`):

```
AssertionError: Lists differ: ['P00[19 chars] 'P003', 'P004', 'P005', 'P006', 'P007', 'P008[133 chars]024'] != ['P00[19 chars] 'P004', 'P005', 'P006', 'P007', 'P008', 'P009[117 chars]024']

First differing element 3:
'P003'
'P004'

First list contains 2 additional elements.
First extra element 24:
'P023'

  ['P001',
   'P002',
-  'P003',
   'P003',
   'P004',
   'P005',
   'P006',
   'P007',
   'P ...
```

### B2: Zero threshold replaced by the default

- **Type:** falsy-zero
- **Symptom:** Test 1: P004, P008 and P023 (all spam) are routed human with low_confidence instead of auto. Test 2: P023 enters the queue and the backlog grows to 7 items. Test 3: spam shows auto 0, human 5, human_rate 1.0; backlog_size 7.
- **Location:** `triage/models.py` → `Thresholds.for_task`
- **Why it fails:** spam has a threshold of 0, which `or` treats as missing and swaps for the 0.8 default, so low-scored spam items are sent to humans.
- **Unblocks:** test_routes for P004/P008/P023.

Fix:

```diff
-        return self.by_type.get(task_type) or self.default
+        return self.by_type.get(task_type, self.default)
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_reasons`):

```
AssertionError: {'P004': 'low_confidence', 'P005': 'flagged', [332 chars]nce'} != {'P005': 'flagged', 'P006': 'no_score', 'P010'[254 chars]nce'}
- {'P004': 'low_confidence',
-  'P005': 'flagged',
? ^

+ {'P005': 'flagged',
? ^

   'P006': 'no_score',
-  'P008': 'low_confidence',
   'P010': 'low_confidence',
   'P012': 'flagged',
   'P013': 'low_confidence',
   'P014': 'no_score',
   'P015': 'low_c ...
```

### B3: Confidence equal to the threshold not accepted

- **Type:** off-by-one
- **Symptom:** Test 1: P002 and P011 are routed human with low_confidence instead of auto. Test 2: both enter the queue, R01 gets P013 instead of P010 and the backlog grows to 7. Test 3: intent becomes auto 1 / human 6 (0.857), toxicity changes too; backlog_size 7.
- **Location:** `triage/router.py` → `route_one`
- **Why it fails:** Rule 3 accepts confidence >= threshold. P002 (toxicity 0.90 vs 0.9) and P011 (intent 0.80 vs 0.8) sit exactly on the threshold and get sent to review.
- **Unblocks:** test_routes and test_reasons for P002/P011.

Fix:

```diff
-    if pred.confidence > threshold:
+    if pred.confidence >= threshold:
```

Observed with only this bug applied (`tests.test_1_routing.TestRouting.test_reasons`):

```
AssertionError: {'P002': 'low_confidence', 'P005': 'flagged', [332 chars]nce'} != {'P005': 'flagged', 'P006': 'no_score', 'P010'[254 chars]nce'}
- {'P002': 'low_confidence',
-  'P005': 'flagged',
? ^

+ {'P005': 'flagged',
? ^

   'P006': 'no_score',
   'P010': 'low_confidence',
-  'P011': 'low_confidence',
   'P012': 'flagged',
   'P013': 'low_confidence',
   'P014': 'no_score',
   'P015': 'low_c ...
```

### B4: Queue filter compares the Enum to a string

- **Type:** enum-vs-string
- **Symptom:** Test 2: the queue, every assignment list and the backlog are empty, although Test 1 shows 13 human decisions. Test 3: backlog_size 0 and busiest_reviewer 'R01' instead of 'R02'. Test 1 passes.
- **Location:** `triage/review_queue.py` → `build_queue`
- **Why it fails:** route is a Route enum member; a plain Enum never equals its value string, so nothing passes the filter and the queue, assignments and backlog are all empty.
- **Unblocks:** test_queue_order/test_assignments/test_backlog (and exposes B5).

Fix:

```diff
-d.route == "human"
+d.route is Route.HUMAN
```

Observed with only this bug applied (`tests.test_2_review_queue.TestReviewQueue.test_assignments`):

```
AssertionError: {'R01': [], 'R02': [], 'R03': [], 'R04': [], 'R06'[33 chars]: []} != {'R01': ['P012', 'P010'], 'R02': ['P005', 'P013', [93 chars]16']}
- {'R01': [],
-  'R02': [],
+ {'R01': ['P012', 'P010'],
+  'R02': ['P005', 'P013', 'P024'],
-  'R03': [],
+  'R03': ['P015'],
?          ++++++

   'R04': [],
-  'R06': [],
+  'R06': ['P019'],
?          ++++++

-  'R08': [],
+  'R08': ['P006'],
?   ...
```

### B5: Queue sorted least urgent first

- **Type:** sort-direction
- **Symptom:** Only visible after B4 is fixed. Test 2: the queue starts with P014, P020 (priority 1) instead of P005, P012 (priority 5), and the backlog becomes P019, P018, P005, P012, so the most urgent items go unreviewed.
- **Location:** `triage/review_queue.py` → `queue_key`
- **Why it fails:** In this repo higher priority numbers are more urgent. Sorting on +priority puts priority-1 items first, so they take reviewer capacity and the urgent items land in the backlog.
- **Unblocks:** test_queue_order, test_assignments, test_backlog and test_busiest_reviewer.
- **Masked:** invisible until B4 is fixed (identical test output either way).

Fix:

```diff
-    return (pred.priority, score, pred.pred_id)
+    return (-pred.priority, score, pred.pred_id)
```

Observed with only this bug applied (`tests.test_2_review_queue.TestReviewQueue.test_assignments`):

```
AssertionError: {'R01': ['P020', 'P016'], 'R02': ['P014', 'P006', 'P0[90 chars]10']} != {'R01': ['P012', 'P010'], 'R02': ['P005', 'P013', 'P0[90 chars]16']}
- {'R01': ['P020', 'P016'],
?              -       ^

+ {'R01': ['P012', 'P010'],
?             +        ^

-  'R02': ['P014', 'P006', 'P015'],
+  'R02': ['P005', 'P013', 'P024'],
-  'R03': ['P024'],
?             ^^

+  'R03': ['P015'],
?     ...
```

### B6: groupby over data not sorted by task type

- **Type:** groupby-misuse
- **Symptom:** Test 3 only: by_task_type comes out as toxicity 0/1 (rate 1.0), sentiment 0/1, spam 1/0, intent 1/0, i.e. only the last consecutive run of each type, instead of intent 2/5, sentiment 3/2, spam 3/2, toxicity 3/4.
- **Location:** `triage/reports.py` → `summarize`
- **Why it fails:** itertools.groupby only groups consecutive items. Sorted by pred_id the task types are interleaved, so each type yields many small groups and the dict keeps only the last run's counts.
- **Unblocks:** test_by_task_type.
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-    ordered = sorted(decisions, key=lambda d: d.prediction.pred_id)
+    ordered = sorted(decisions, key=lambda d: d.prediction.task_type)
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_by_task_type`):

```
AssertionError: {'toxicity': {'auto': 0, 'human': 1, 'human[171 chars]0.0}} != {'intent': {'auto': 2, 'human': 5, 'human_r[175 chars]571}}
Diff is 923 characters long. Set self.maxDiff to None to see it.
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `triage/assigner.py` → `pick_reviewer`: min() over (-remaining, id) looks backwards for 'most remaining capacity', but negating remaining makes the largest capacity the smallest key, and the id breaks ties ascending, exactly as rule 6 says.
- `triage/utils.py` → `parse_ts`: It covers exactly the three formats in the README, with day.month.year for the dotted one.
