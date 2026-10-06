# set-083 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do?

It loads the labeler registry (id -> active flag), the pairs, and both judgement files, screens labelers with `quality.labeler_quality` on the calibration judgements, keeps the non-excluded labelers, aggregates the regular judgements with `aggregate.aggregate`, and builds the dataset and standings from those results.

### 2. How does latest_only pick a judgement?

It keys on `(pair_id, labeler_id)` and replaces the stored judgement whenever the new one's `submitted_at` is `>=` the stored one, so the latest wins and, on equal times, the later row. Output order is first-seen key order.

### 3. What does margin_of return?

It decides whether model_a was on the left by comparing the judgement's `left_model` against `pair.model_a`, then returns `a_margin(rating, left_is_a)`.

### 4. How is left_model stored by the loader?

`load_judgements` stores it with `clean()`, i.e. trimmed but with its original case. Pair model names go through `norm_model` in `load_pairs`.

### 5. Which labelers appear in the quality table?

Every labeler whose active flag is true, sorted by id. `checks` is how many calibration judgements were counted for them in `labeler_quality`; accuracy is None when that is 0.

### 6. How does standings count a tie?

Both models get one entry in `ties`. Win rate is `(wins + 0.5 * ties) / games` rounded to 3 decimals; pairs with verdict `insufficient` are skipped.
