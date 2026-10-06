# set-026 answer key: Tone-label agreement with per-project quorum

**Domain:** annotation_consensus  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_tasks.TestTasks.test_vote_counts` | B1 Resubmissions not collapsed |
| `test_1_tasks.TestTasks.test_statuses` | B2 Exactly min_votes treated as too few |
| `test_2_agreement.TestAgreement.test_agreement_rates` | B3 Skips counted as disagreeing votes |
| `test_2_agreement.TestAgreement.test_low_and_unscored_annotators` | B4 Zero agreement reported as None |
| `test_3_report.TestReport.test_labels_by_project` | B5 Per-project label counts accumulate |
| `test_3_report.TestReport.test_team_summary` | B6 Roster read without stripping the BOM |

## Failing pattern with all bugs present

- `tests.test_1_tasks.TestTasks.test_statuses`
- `tests.test_1_tasks.TestTasks.test_vote_counts`
- `tests.test_2_agreement.TestAgreement.test_agreement_rates`
- `tests.test_2_agreement.TestAgreement.test_low_and_unscored_annotators`
- `tests.test_3_report.TestReport.test_labels_by_project`
- `tests.test_3_report.TestReport.test_team_summary`

## Bugs (recommended order)

### B1: Resubmissions not collapsed

- **Type:** missing-dedupe
- **Symptom:** Test 1 test_vote_counts: C-04 shows 5 votes (expected 4) and E-06 shows 4 (expected 3). Every status and label is still right.
- **Location:** `tonevote/loader.py` → `load_annotations`
- **Why it fails:** The dedupe helper is never called, so a09's two C-04 rows and a11's two E-06 rows are both counted as votes. Neither task changes status, so only the vote counts show it.
- **Failing test:** `test_1_tasks.TestTasks.test_vote_counts`
- **Unblocks:** test_1_tasks test_vote_counts.

Fix:

```diff
-    return annotations
+    return latest_per_annotator(annotations)
```

Observed with only this bug applied (`tests.test_1_tasks.TestTasks.test_vote_counts`):

```
AssertionError: {'C-0[32 chars]04': 5, 'C-05': 5, 'C-06': 2, 'C-07': 4, 'E-01[110 chars]': 2} != {'C-0[32 chars]04': 4, 'C-05': 5, 'C-06': 2, 'C-07': 4, 'E-01[110 chars]': 2}
  {'C-01': 4,
   'C-02': 4,
   'C-03': 3,
-  'C-04': 5,
?          ^

+  'C-04': 4,
?          ^

   'C-05': 5,
   'C-06': 2,
   'C-07': 4,
   'E-01': 2,
   'E-02': 3,
   'E-03': 3,
   'E-04': 1,
   'E-05': 3,
-  'E-06': 4,
? ...
```

### B2: Exactly min_votes treated as too few

- **Type:** off-by-one
- **Symptom:** Test 1 test_statuses: C-03, E-01 and R-01 are 'pending' instead of 'escalated'. Each has exactly its project's min_votes votes.
- **Location:** `tonevote/consensus.py` → `resolve`
- **Why it fails:** Rule 3 says exactly min_votes is enough to decide. `<=` sends every task with exactly the quorum to pending. In this data all of those tasks are escalated (C-03, E-01, R-01), so only the status map changes.
- **Failing test:** `test_1_tasks.TestTasks.test_statuses`
- **Unblocks:** test_1_tasks test_statuses.

Fix:

```diff
-        if len(labels) <= project.min_votes:
+        if len(labels) < project.min_votes:
```

Observed with only this bug applied (`tests.test_1_tasks.TestTasks.test_statuses`):

```
AssertionError: {'C-0[36 chars]3': 'pending', 'C-04': 'escalated', 'C-05': 'a[244 chars]ing'} != {'C-0[36 chars]3': 'escalated', 'C-04': 'escalated', 'C-05': [250 chars]ing'}
  {'C-01': 'agreed',
   'C-02': 'agreed',
-  'C-03': 'pending',
+  'C-03': 'escalated',
   'C-04': 'escalated',
   'C-05': 'agreed',
   'C-06': 'pending',
   'C-07': 'agreed',
-  'E-01': 'pending',
+  'E-01': 'escalated',
    ...
```

### B3: Skips counted as disagreeing votes

- **Type:** counting-wrong-subset
- **Symptom:** Test 2 test_agreement_rates: a06 shows agreed_tasks 5 / agreement 0.8 (expected 4 / 1.0) and a08 shows 6 / 0.333 (expected 4 / 0.5). Skip counts are right.
- **Location:** `tonevote/agreement.py` → `agreement_table`
- **Why it fails:** Without the `continue`, a skip on an agreed task falls through and is counted as a vote that didn't match. a06 (skipped R-03) and a08 (skipped C-07 and E-05) get extra agreed_tasks and lower agreement.
- **Failing test:** `test_2_agreement.TestAgreement.test_agreement_rates`
- **Unblocks:** test_2_agreement test_agreement_rates.

Fix:

```diff
             skips[aid] += 1
+            continue
```

Observed with only this bug applied (`tests.test_2_agreement.TestAgreement.test_agreement_rates`):

```
AssertionError: {'a01[308 chars]ks': 5, 'agreement': 0.8, 'skips': 1}, 'a07': [164 chars]: 0}} != {'a01[308 chars]ks': 4, 'agreement': 1.0, 'skips': 1}, 'a07': [162 chars]: 0}}
  {'a01': {'agreed_tasks': 6, 'agreement': 1.0, 'skips': 0},
   'a02': {'agreed_tasks': 5, 'agreement': 0.8, 'skips': 1},
   'a03': {'agreed_tasks': 5, 'agreement': 0.8, 'skips': 0},
   'a04': {'agreed_tasks': 3, 'agreement ...
```

### B4: Zero agreement reported as None

- **Type:** falsy-zero
- **Symptom:** Test 2 test_low_and_unscored_annotators: a10 shows agreement None (expected 0.0) even though agreed_tasks is 4.
- **Location:** `tonevote/reports.py` → `build_report`
- **Why it fails:** a10 disagreed on all 4 agreed tasks, so the rate is 0.0. A truthiness check treats 0.0 like a missing rate and prints None, which the spec reserves for annotators with no agreed tasks.
- **Failing test:** `test_2_agreement.TestAgreement.test_low_and_unscored_annotators`
- **Unblocks:** test_2_agreement test_low_and_unscored_annotators.

Fix:

```diff
-round(row.rate, 3) if row.rate else None
+round(row.rate, 3) if row.rate is not None else None
```

Observed with only this bug applied (`tests.test_2_agreement.TestAgreement.test_low_and_unscored_annotators`):

```
AssertionError: {'agreed_tasks': 4, 'agreement': None, 'skips': 0} != {'agreed_tasks': 4, 'agreement': 0.0, 'skips': 0}
- {'agreed_tasks': 4, 'agreement': None, 'skips': 0}
?                                  ^^^^

+ {'agreed_tasks': 4, 'agreement': 0.0, 'skips': 0}
?                                  ^^^
```

### B5: Per-project label counts accumulate

- **Type:** mutable-default
- **Symptom:** Test 3 test_labels_by_project: the per-project counts keep growing (in a full-suite run chat shows negative 7, neutral 4, positive 13). The overall counts are right.
- **Location:** `tonevote/consensus.py` → `count_labels`
- **Why it fails:** The default Counter is created once, when the function is defined, so every call without `counts` adds to the same object. Each project's breakdown includes the projects before it (and earlier build_report calls). The overall count passes its own Counter, so it stays right.
- **Failing test:** `test_3_report.TestReport.test_labels_by_project`
- **Unblocks:** test_3_report test_labels_by_project.

Fix:

```diff
-def count_labels(results, counts=Counter()):
+def count_labels(results, counts=None):
     """Add the agreed labels in `results` to `counts` (a fresh Counter by default)."""
+    if counts is None:
+        counts = Counter()
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_labels_by_project`):

```
AssertionError: {'chat': {'negative': 7, 'neutral': 4, 'positive': 13}, 'email'[101 chars] 15}} != {'chat': {'negative': 1, 'positive': 3}, 'email': {'negative': [84 chars]: 1}}
- {'chat': {'negative': 7, 'neutral': 4, 'positive': 13},
?                       ^ --------------             -

+ {'chat': {'negative': 1, 'positive': 3},
?                       ^

-  'email': {'negative': 8, 'neutral': ...
```

### B6: Roster read without stripping the BOM

- **Type:** csv-bom-encoding
- **Symptom:** Test 3 test_team_summary: teams comes back as {} (expected east/north/south/west with members and votes).
- **Location:** `tonevote/utils.py` → `read_rows`
- **Why it fails:** teams.csv starts with a UTF-8 BOM. Read as plain utf-8, the first header becomes '\ufeffannotator_id', so `row.get("annotator_id")` is None for every row and the roster comes back empty. The batch files have no BOM, so nothing else changes.
- **Failing test:** `test_3_report.TestReport.test_team_summary`
- **Unblocks:** test_3_report test_team_summary.

Fix:

```diff
-    with open(path, newline="", encoding="utf-8") as fh:
+    with open(path, newline="", encoding="utf-8-sig") as fh:
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_team_summary`):

```
AssertionError: {} != {'east': {'members': ['a07', 'a08', 'a10'][175 chars]: 0}}
- {}
+ {'east': {'members': ['a07', 'a08', 'a10'], 'votes': 13},
+  'north': {'members': ['a01', 'a02', 'a03'], 'votes': 23},
+  'south': {'members': ['a04', 'a05', 'a06'], 'votes': 20},
+  'west': {'members': ['a12', 'a13'], 'votes': 0}}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `tonevote/consensus.py` → `decide`: The `>=` looks like it might need to be `>`, but README rule 5 says a share at or above the bar is agreed (C-01 is exactly 3/4 = 0.75). The explicit tie check implements rule 4, so R-01's 2-2 split escalates even though 0.5 meets the reviews bar.
- `tonevote/utils.py` → `parse_timestamp`: The day.month.year format looks like it clashes with month/day/year, but the separators differ (`.` vs `/`), so each string matches exactly one format, and both are listed in the README.
