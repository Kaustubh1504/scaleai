# set-098 answer key: Two-vendor tiered consensus with deadlines

**Domain:** annotation_consensus  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_screening.TestScreening.test_rejected_by_vendor` | B1 Rejection dict as a mutable default |
| `test_1_screening.TestScreening.test_superseded` | B2 Vendor B seconds treated as milliseconds |
| `test_2_consensus.TestConsensus.test_tox_items` | B3 Tier compared with a string |
| `test_2_consensus.TestConsensus.test_spam_items` | B4 Vote at the deadline excluded |
| `test_3_report.TestQualityReport.test_annotator_agreement` | B5 Agreement counts escalated items |
| `test_3_report.TestQualityReport.test_contested` | B6 and/or precedence in contested filter |

## Failing pattern with all bugs present

- `tests.test_1_screening.TestScreening.test_rejected_by_vendor`
- `tests.test_1_screening.TestScreening.test_superseded`
- `tests.test_2_consensus.TestConsensus.test_spam_items`
- `tests.test_2_consensus.TestConsensus.test_tox_items`
- `tests.test_3_report.TestQualityReport.test_annotator_agreement`
- `tests.test_3_report.TestQualityReport.test_contested`

## Bugs (recommended order)

### B1: Rejection dict as a mutable default

- **Type:** mutable-default
- **Symptom:** Test 1 test_rejected_by_vendor: vendor_a and vendor_b both list all nine rejections (A-0xx and b-10xx together). Which votes count is unchanged, so every consensus result is still right.
- **Location:** `quorum/screening.py` → `screen`
- **Why it fails:** `rejected={}` is evaluated once, when the function is defined. Both screen() calls (and every later build_report) write into that same dict, so each vendor's 'own' rejections are the same shared object.
- **Failing test:** `test_1_screening.TestScreening.test_rejected_by_vendor`
- **Unblocks:** test_1_screening.TestScreening.test_rejected_by_vendor

Fix:

```diff
-def screen(votes, items, annotators, queues, aliases, rejected={}):
+def screen(votes, items, annotators, queues, aliases, rejected=None):
     """Return (accepted votes with canonical labels, {vote_id: reason})."""
+    rejected = {} if rejected is None else rejected
```

Observed with only this bug applied (`tests.test_1_screening.TestScreening.test_rejected_by_vendor`):

```
AssertionError: {'ven[121 chars]abel', 'b-1019': 'unknown_annotator', 'b-1020'[313 chars]el'}} != {'ven[121 chars]abel'}, 'vendor_b': {'b-1019': 'unknown_annota[82 chars]el'}}
Diff is 885 characters long. Set self.maxDiff to None to see it.
```

### B2: Vendor B seconds treated as milliseconds

- **Type:** ms-vs-s
- **Symptom:** Test 1 test_superseded: ['A-003', 'b-1006'] instead of ['A-003', 'A-016']. a03's S03 vote via vendor A is kept over their later vendor B vote. Consensus is unchanged because both votes say 'ham'.
- **Location:** `quorum/timeutil.py` → `from_epoch`
- **Why it fails:** vendor_b.jsonl stores Unix seconds. Dividing by 1000 puts every vendor B vote in January 1970, so in the cross-vendor 'latest answer' rule the vendor A vote always looks newer.
- **Failing test:** `test_1_screening.TestScreening.test_superseded`
- **Unblocks:** test_1_screening.TestScreening.test_superseded

Fix:

```diff
-    return datetime.fromtimestamp(seconds / 1000, tz=timezone.utc)
+    return datetime.fromtimestamp(seconds, tz=timezone.utc)
```

Observed with only this bug applied (`tests.test_1_screening.TestScreening.test_superseded`):

```
AssertionError: Lists differ: ['A-003', 'b-1006'] != ['A-003', 'A-016']

First differing element 1:
'b-1006'
'A-016'

- ['A-003', 'b-1006']
?            ^  --

+ ['A-003', 'A-016']
?            ^ +
```

### B3: Tier compared with a string

- **Type:** enum-vs-string
- **Symptom:** Test 2 test_tox_items: T02 is labelled 'clean' instead of 'toxic'. Status and agreement are unchanged (escalated, 0.5).
- **Location:** `quorum/voting.py` → `expert_votes`
- **Why it fails:** Tier is a plain Enum, so `Tier.EXPERT == "expert"` is False and every label gets 0 expert votes. T02 is a 3-3 weight tie in which the only expert voted toxic, and without the expert count the alphabetical fallback picks 'clean'.
- **Failing test:** `test_2_consensus.TestConsensus.test_tox_items`
- **Unblocks:** test_2_consensus.TestConsensus.test_tox_items

Fix:

```diff
-    return sum(1 for v in votes if v.label == label and annotators[v.annotator_id].tier == "expert")
+    return sum(1 for v in votes if v.label == label and annotators[v.annotator_id].tier is Tier.EXPERT)
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_tox_items`):

```
AssertionError: {'T01[113 chars]l': 'clean', 'agreement': 0.5, 'votes': 3}, 'T[149 chars]: 2}} != {'T01[113 chars]l': 'toxic', 'agreement': 0.5, 'votes': 3}, 'T[149 chars]: 2}}
  {'T01': {'agreement': 0.714,
           'label': 'toxic',
           'status': 'accepted',
           'votes': 3},
-  'T02': {'agreement': 0.5, 'label': 'clean', 'status': 'escalated', 'votes': 3},
?                       ...
```

### B4: Vote at the deadline excluded

- **Type:** time-window-boundary
- **Symptom:** Test 2 test_spam_items: S02 comes out as phishing / 0.6 with 2 votes instead of spam / 0.571 with 3 votes.
- **Location:** `quorum/voting.py` → `within_window`
- **Why it fails:** Rule 7 counts a vote submitted exactly at closes_at. With `<`, a04's 12:00 vote on S02 is dropped, and that flips the leading label.
- **Failing test:** `test_2_consensus.TestConsensus.test_spam_items`
- **Unblocks:** test_2_consensus.TestConsensus.test_spam_items

Fix:

```diff
-vote.submitted_at < item.closes_at
+vote.submitted_at <= item.closes_at
```

Observed with only this bug applied (`tests.test_2_consensus.TestConsensus.test_spam_items`):

```
AssertionError: {'S01[110 chars]l': 'phishing', 'agreement': 0.6, 'votes': 2},[155 chars]: 3}} != {'S01[110 chars]l': 'spam', 'agreement': 0.571, 'votes': 3}, '[153 chars]: 3}}
Diff is 646 characters long. Set self.maxDiff to None to see it.
```

### B5: Agreement counts escalated items

- **Type:** counting-wrong-subset
- **Symptom:** Test 3 test_annotator_agreement: a03 shows 0.5 instead of 1.0 in the quality queue. Their 'fair' vote on escalated Q03 is being scored.
- **Location:** `quorum/scoring.py` → `annotator_agreement`
- **Why it fails:** Escalated items still carry a leading label, so filtering on `label is None` only skips pending items. The spec scores annotators only on accepted items.
- **Failing test:** `test_3_report.TestQualityReport.test_annotator_agreement`
- **Unblocks:** test_3_report.TestQualityReport.test_annotator_agreement

Fix:

```diff
-        if result is None or result.label is None:
+        if result is None or result.status != "accepted":
```

Observed with only this bug applied (`tests.test_3_report.TestQualityReport.test_annotator_agreement`):

```
AssertionError: {'a01[18 chars], 'a03': 0.5, 'a04': 1.0, 'a07': 1.0, 'a08': 0.0, 'a11': 0.667} != {'a01[18 chars], 'a03': 1.0, 'a04': 1.0, 'a07': 1.0, 'a08': 0.0, 'a11': 0.667}
  {'a01': 1.0,
   'a02': 1.0,
-  'a03': 0.5,
?          --

+  'a03': 1.0,
?         ++

   'a04': 1.0,
   'a07': 1.0,
   'a08': 0.0,
   'a11': 0.667}
```

### B6: and/or precedence in contested filter

- **Type:** or-precedence
- **Symptom:** Test 3 test_contested: ['Q01', 'Q02', 'Q03'] instead of ['Q01', 'Q02']. Q03 is escalated, not accepted.
- **Location:** `quorum/scoring.py` → `contested`
- **Why it fails:** `and` binds tighter than `or`, so the condition reads `(accepted and low agreement) or expert_dissent`. Q03 is escalated but has expert dissent, so it gets in.
- **Failing test:** `test_3_report.TestQualityReport.test_contested`
- **Unblocks:** test_3_report.TestQualityReport.test_contested

Fix:

```diff
-if r.status == "accepted" and r.agreement < CONTESTED_BELOW or r.expert_dissent)
+if r.status == "accepted" and (r.agreement < CONTESTED_BELOW or r.expert_dissent))
```

Observed with only this bug applied (`tests.test_3_report.TestQualityReport.test_contested`):

```
AssertionError: Lists differ: ['Q01', 'Q02', 'Q03'] != ['Q01', 'Q02']

First list contains 1 additional elements.
First extra element 2:
'Q03'

- ['Q01', 'Q02', 'Q03']
?              -------

+ ['Q01', 'Q02']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `quorum/voting.py` → `pick_label`: min() over a negated key looks inverted, but (-weight, -expert votes, label) sorts the heaviest label first, then the one with the most expert votes, then alphabetical: exactly rule 9. The T02 symptom comes from the expert counts passed in, not from this function.
- `quorum/timeutil.py` → `parse_timestamp`: Stripping the trailing 'Z' and parsing naively looks lossy, but every vendor A and item time is UTC per the README, and from_epoch also returns naive UTC, so the two compare correctly.
