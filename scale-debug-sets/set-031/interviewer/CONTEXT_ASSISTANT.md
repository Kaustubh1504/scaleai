# set-031 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads items (sorted by id) and attempts, groups attempts by model then item with `group_attempts`, calls `score_model` per model, and builds `by_category` with `category_accuracy` from the correct ids. Status counts are computed from the raw attempt list per model, and the leaderboard sorts models by (-accuracy, name).

### 2. What type is Attempt.status after loading?

`load_attempts` calls `parse_status`, which returns a member of the `Status` enum in models.py (`Status.OK`, `Status.ERROR` or `Status.TIMEOUT`). `Status` is a plain `Enum` with string values.

### 3. How does select_final pick between several attempts?

It loops over the attempts for one (model, item), skips any whose status is in the tuple it checks, and keeps the one with the largest `attempt` number among the rest. It returns None if nothing survives the filter.

### 4. What does parse_choice return for 'Answer: B ... Answer: C'?

It collects every marker match with `findall` and returns the last one upper-cased, so 'C'. Without any marker it tries a full match of a lone letter, optionally in parentheses and followed by a period, and otherwise returns None.

### 5. Where is the accuracy denominator computed?

In `score_model`, `score.possible` is incremented with each item's weight inside the item loop; `build_report` divides `score.earned` by it. `by_category` is computed separately in `category_accuracy`, which sums weights over all items of each category.

### 6. What counts as an error status?

`parse_status` trims and lower-cases the cell. `ok`/`success` map to OK, the timeout branch maps to TIMEOUT, and everything that falls through (including blank and numeric codes) maps to ERROR.
