# set-022 interviewer notes

**Scenario:** Dedupe re-scored model predictions, route each to auto-accept or human review by per-task-type confidence thresholds and always-human flags, order the review queue by priority (higher = more urgent), and hand it out to language-matched reviewers by remaining capacity. Test 3 summarises routing per task type.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Dedupe key includes created_at

1. **Nudge:** P003 and P009 show up twice in decisions. Find them in predictions.csv.
2. **Area:** Look at how latest_per_prediction decides two rows are the same prediction.
3. **Exact:** The dict key is (pred_id, created_at); it should be just pred.pred_id.

### B2: Zero threshold replaced by the default

1. **Nudge:** P004, P008 and P023 are all spam. What is spam's threshold?
2. **Area:** Look at how the threshold for a task type is looked up.
3. **Exact:** `get(task_type) or self.default` turns 0.0 into 0.8; use get(task_type, self.default).

### B3: Confidence equal to the threshold not accepted

1. **Nudge:** Compare P002's and P011's confidence with their thresholds.
2. **Area:** Look at the comparison that decides auto vs human.
3. **Exact:** route_one uses >; it should be >=.

### B4: Queue filter compares the Enum to a string

1. **Nudge:** The queue is empty even though test 1 shows many human decisions.
2. **Area:** Look at how build_queue picks the human decisions. What type is d.route?
3. **Exact:** Compare with Route.HUMAN (`d.route is Route.HUMAN`), not the string "human".

### B5: Queue sorted least urgent first

1. **Nudge:** Look at where the priority-5 items sit in the queue.
2. **Area:** Read README rule 4 and then the sort key in review_queue.py.
3. **Exact:** queue_key should return (-pred.priority, score, pred.pred_id).

### B6: groupby over data not sorted by task type

1. **Nudge:** The per-type totals in the summary don't add up to 24.
2. **Area:** How does groupby decide where one group ends?
3. **Exact:** Sort by d.prediction.task_type before grouping.

## "Why did that fix work?" probes

**B1**
- Why did P016 still come out once?
- Why does the `>=` in the comparison matter for P016 but not for P003?

**B2**
- Why was P014 (spam, blank confidence) unaffected?
- What would a threshold written as "0" in the JSON have done before float() conversion?

**B3**
- Why did P007 (0.80, sentiment) stay auto?
- Is comparing floats with >= safe here? When would it not be?

**B4**
- Why does d.route.value == "human" work but d.route == "human" not?
- What change to the Route class would have made the string comparison work?

**B5**
- Why was this invisible until the Enum comparison was fixed?
- The comment says 'most urgent first'. What convention did the author assume?

**B6**
- Why didn't Python raise an error when the same key came out of groupby twice?
- How would a Counter or defaultdict avoid the sort requirement?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `triage/assigner.py` → `pick_reviewer`: min() over (-remaining, id) looks backwards for 'most remaining capacity', but negating remaining makes the largest capacity the smallest key, and the id breaks ties ascending, exactly as rule 6 says.
- `triage/utils.py` → `parse_ts`: It covers exactly the three formats in the README, with day.month.year for the dotted one.
