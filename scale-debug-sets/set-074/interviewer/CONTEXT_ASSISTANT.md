# set-074 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, in order?

It loads config, registry and items, reads every data/ratings_*.csv with read_ratings, filters them with counting_ratings, takes the gold subset with gold_ratings, creates one Memo, runs consensus.resolve, then builds the bias table by calling bias_for for every active annotator and rubric, and finally the summary.

### 2. What does counting_ratings filter on?

Known item id, registry.get(annotator_id) being truthy, the submitted date compared with config opens/closes, and then it keeps the rating with the greatest submitted_at per (item_id, annotator_id).

### 3. How does Memo work?

get_or_compute(key, compute) calls compute() only the first time a key is seen, stores the result in a dict and returns the stored value afterwards. One Memo is created per build_report call; misses counts how many computes ran.

### 4. Where is bias_for called from?

From consensus.resolve, once per counting rating on a non-gold item with that item's rubric, and from build_report when the bias table is built. Both pass the same Memo.

### 5. How are votes for an item computed?

resolve groups ratings by item id, and for each non-gold item maps every rating through adjust(r.score, bias_for(..., r.annotator_id, item.rubric)). Gold items are skipped entirely.

### 6. What does rubric_summary return?

A dict rubric -> {'agreed': n, 'contested': n, 'insufficient': n}, built by grouping Result objects by r.rubric with itertools.groupby and counting statuses with a Counter.

### 7. Which order are items processed in?

items is a dict filled in items.csv file order, so resolve walks G1, I01, I02, G3, I03, ... and the results dict is in that same order (gold items omitted).
