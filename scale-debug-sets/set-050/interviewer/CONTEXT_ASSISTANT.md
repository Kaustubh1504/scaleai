# set-050 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens in build_report(), step by step?

It loads the registry and items, reads ratings (dropping blanks, out-of-range values and unknown annotators), splits off rushed submissions with split_rushed, keeps one submission per key with latest_only, then score_items builds the per-item results and the list of outlier ratings. Counters over the remaining ratings and the outliers feed the annotators table, and summarize builds the summary.

### 2. What does split_rushed return?

A list of the submissions whose duration_seconds is at least MIN_SECONDS (20), and a Counter of annotator id → number of submissions under that.

### 3. How does latest_only choose between two submissions with the same key?

It keeps the stored one unless the new one's finished_at is greater than or equal to it, so the latest wins and a later row wins a tie. The output is in first-seen key order.

### 4. In score_items, which check runs first: adjudication or the minimum count?

Adjudication. An item with adjudicated_rating set is marked ADJUDICATED with that consensus before the MIN_RATINGS (3) check runs.

### 5. What does drop_outliers compare each rating against?

The median of all the item's counted ratings, computed once before the loop; ratings more than OUTLIER_GAP (3) away are moved to the outliers list.

### 6. What type is ItemResult.status, and how does it reach the report?

It is a `Status` member (a plain Enum). The report's items section and status_counts convert it with `.value`.

### 7. Which items feed category_means?

Every item whose consensus is not None, including adjudicated ones, grouped by the item's category from items.csv.
