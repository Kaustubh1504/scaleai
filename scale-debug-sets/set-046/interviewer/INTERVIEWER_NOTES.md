# set-046 interviewer notes

**Scenario:** Model predictions are auto-accepted or sent to humans by per-(model, label) thresholds, the human queue is assigned to language-matched reviewers by priority (1 = most urgent) and capacity, and a calibration report plus JSON export round it off.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Threshold cache keyed by label only

1. **Nudge:** Compare the threshold reported for P-03 with the v2 spam row in thresholds.csv.
2. **Area:** The table resolves correctly; look at what is remembered between lookups.
3. **Exact:** ThresholdTable.lookup caches by `label`; the key must be `(model_version, label)`.

### B2: Confidence equal to threshold sent to humans

1. **Nudge:** Which single item changed decision? Compare its confidence to its threshold.
2. **Area:** Check the comparison in route_one against README rule 3.
3. **Exact:** `pred.confidence > threshold` should be `>=`.

### B3: Queue sorted least urgent first

1. **Nudge:** English has 6 human items and 5 slots. Which one should be left over?
2. **Area:** Look at how the queue is ordered before assignment.
3. **Exact:** review_queue sorts by `-p.priority`; README rule 4 says 1 is most urgent, so sort by `p.priority`.

### B4: Capacity 0 replaced by the default

1. **Nudge:** r-07 got work. Look them up in reviewers.json.
2. **Area:** Look at how capacity is read in the loader.
3. **Exact:** `int(item.get('capacity') or DEFAULT_CAPACITY)` turns 0 into 2; only apply the default for None or blank.

### B5: Counter.update fed a string

1. **Nudge:** What are the keys in reviewer_mix? Do they look like labels?
2. **Area:** Look at how each reviewer's Counter is updated.
3. **Exact:** `update(r.human_label)` should be `update([r.human_label])` (or `[label] += 1`).

### B6: Datetimes exported with str()

1. **Nudge:** Compare the exported timestamp string character by character with the expected one.
2. **Area:** How does export_json turn non-JSON types into strings?
3. **Exact:** Use `default=_encode` instead of `default=str`.

## "Why did that fix work?" probes

**B1**
- Why did every decision stay the same even though the thresholds changed?
- What input order would have made this cache return the v2 value for v1 items instead?

**B2**
- Why didn't the extra human item change any reviewer's assignments?
- Floats: could 75% and 0.75 ever compare unequal here? Why not?

**B3**
- Why were the German assignments unaffected by the queue order?
- The comment says 'most urgent first'. What in the data tells you which end is urgent?

**B4**
- r-06 has a blank capacity and r-10 has none. Why must both still get 2?
- Why did r-07 get P-17 but not P-10?

**B5**
- Why did `agreement` come out right while reviewer_mix did not?
- What would `Counter('spam')` and `Counter(['spam'])` each return?

**B6**
- Why didn't json.dumps raise on the datetime values?
- What would `default=str` do to a set of languages if one were added to the report?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `routedesk/utils.py` → `parse_confidence`: Dividing only when the number is above 1 looks like it mishandles values such as `1%`, but the README defines any value above 1 as a percentage, so `1` is 1.0 and `91`/`91%` are 0.91. Blank values return None as the spec requires.
- `routedesk/loader.py` → `latest_by_item`: The `>=` looks like it should be `>`, but the spec says that on equal timestamps the later row wins. It compares parsed datetimes, so the mixed formats order correctly, and the id is normalised before the lookup so ` P-05`/`p-02` collapse onto their twins.
