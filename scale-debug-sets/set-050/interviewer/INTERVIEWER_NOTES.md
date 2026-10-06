# set-050 interviewer notes

**Scenario:** Rushed and superseded submissions are dropped, each item's consensus is a median after a single outlier pass, low-agreement items are escalated and expert adjudications override; the summary reports status counts, escalations and per-category means.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Duration read with timedelta.seconds

1. **Nudge:** ann-07 is counted as rushed. Find their submissions and compute each duration.
2. **Area:** Look at how a submission's duration is measured.
3. **Exact:** Use total_seconds() instead of .seconds.

### B2: Resubmissions deduped by submission id

1. **Nudge:** I-04 has five counted ratings. How many annotators rated it?
2. **Area:** Look at what latest_only uses to recognise the same submission twice.
3. **Exact:** Key on (item_id, annotator_id), not submission_id.

### B3: Even-count median uses floor division

1. **Nudge:** Only I-06 is off, by exactly 0.5. What is special about its ratings?
2. **Area:** Look at the even-length branch of median().
3. **Exact:** Use `/ 2`, not `// 2`.

### B4: Outliers removed while iterating the same list

1. **Nudge:** ann-05's 1 on I-08 is 7 points from the median. Why isn't it an outlier?
2. **Area:** Look at how drop_outliers walks and edits the list.
3. **Exact:** Iterate over a copy: `for r in list(kept):`.

### B5: Category total not reset per category

1. **Nudge:** coding is right but writing is far too high. What comes between them?
2. **Area:** Where is the running total initialised in category_means?
3. **Exact:** Move `total = 0.0` inside the `for cat` loop.

### B6: Enum status compared to a string

1. **Nudge:** status_counts says 2 escalated, but the escalated list is empty.
2. **Area:** Compare how summarize builds status_counts and escalated.
3. **Exact:** Compare with Status.ESCALATED (or res.status.value == 'escalated').

## "Why did that fix work?" probes

**B1**
- Why didn't dropping s-040 change I-09's consensus or status?
- What does timedelta(days=1, seconds=12).seconds return, and why?

**B2**
- Why did I-04's consensus stay 7 even with the extra rating?
- Which other field of the report would show ann-01's extra rating?

**B3**
- Why were I-02, I-04 and I-09 right even though they also have an even number of ratings?
- Why did I-06's status not change?

**B4**
- Why did I-07's single outlier still get removed?
- Why did I-08's consensus stay 8 even with the 1 left in?

**B5**
- Why is the first category always right with this mistake?
- How would `sum(values) / len(values)` have avoided it?

**B6**
- Would `class Status(str, Enum)` have made the comparison work? Why?
- Why does no error get raised?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `ratingpanel/utils.py` → `parse_rating`: `int(float(text))` looks like it silently truncates, but the README says ratings are whole numbers sometimes written as `6.0`, so float-then-int is exactly what is needed; blanks and out-of-range values return None.
- `ratingpanel/scoring.py` → `agreement`: `<= 1` looks like it should be `< 1`, but the spec counts ratings within 1 point inclusive. It divides by the number of remaining ratings and rounds to 3 decimals as required.
