# set-094 interviewer notes

**Scenario:** Route moderation predictions to auto / expert / crowd by label threshold, sensitivity, flags and severity (5 = most severe), with legacy models never auto-accepting. Expert items are assigned per language pool (least-loaded, seniors only for severity 5). Test 3 is a calibration report from yesterday's human reviews.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Threshold 0.0 replaced by the default

1. **Nudge:** M01 and M03 are promo predictions. What is promo's threshold in policy.json?
2. **Area:** Look at how a null threshold is turned into the default.
3. **Exact:** Use `rule.threshold if rule.threshold is not None else self.default_threshold`.

### B2: Legacy-model check compares an Enum to a string

1. **Nudge:** L01, L02 and L04 come from guard-v1, which is in legacy_models. Why are they auto?
2. **Area:** Put a breakpoint on the legacy check in decide(). What type is `route` there?
3. **Exact:** Compare against the enum: `route is Route.AUTO`.

### B3: and/or precedence lets any senior take any item

1. **Nudge:** rv-06 is inactive, yet has items. Which property of rv-06 makes the code think they can take work?
2. **Area:** Read eligible() slowly. Which operators group together?
3. **Exact:** Parenthesise the senior clause: `... and (severity < SENIOR_ONLY_SEVERITY or reviewer.senior)`.

### B4: Reviewer pool not lower-cased

1. **Nudge:** rv-02 is active with capacity 2 but got nothing. Which pool does the code put rv-02 in?
2. **Area:** Compare how item languages and reviewer pools are cleaned in loader.py.
3. **Exact:** load_reviewers needs `clean(row["pool"]).lower()`.

### B5: Confusion ties broken by insertion order

1. **Nudge:** promo was confused with spam once and with off_topic once. Which should win?
2. **Area:** How does label_confusions choose among equal counts?
3. **Exact:** Use min(counts, key=lambda h: (-counts[h], h)).

### B6: groupby over unsorted reviews

1. **Nudge:** guard-v3 has 9 usable reviews. How many does the table report?
2. **Area:** What does itertools.groupby assume about the order of its input?
3. **Exact:** Sort before grouping: groupby(sorted(reviews, key=_model), key=_model).

## "Why did that fix work?" probes

**B1**
- Why was M02 still auto-accepted?
- Why did nothing change in the expert assignments?

**B2**
- What would Route(str, Enum) have changed here?
- Why does `d.route.value` in reports.py work while this comparison doesn't?

**B3**
- Why didn't the English pool change, even though rv-01 is a senior too?
- Which data would make this show up in the German pool?

**B4**
- Why was the item side ('EN' in I02, 'DE' in I16) fine?
- Would a set of pools built from reviewers.csv have caught this sooner?

**B5**
- Why did harassment come out right?
- Would sorting reviews.csv change the buggy answer? Is that a fix?

**B6**
- Why does test_models_listed still pass?
- How would you write this with a defaultdict(list) instead, and is it better?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `hitlroute/assign.py` → `queue_order`: The minus on severity looks like a flipped sort, but 5 is the most severe, so ascending on -severity handles severity 5 first. Then earliest received_at, then item_id, exactly as rule 9 says.
- `hitlroute/loader.py` → `parse_confidence`: The comma replace and the percent branch look like guesswork, but the README lists exactly these formats: '0,90' and '88%' must come out as 0.9 and 0.88. Blank returns None, which the router treats as no_confidence.
