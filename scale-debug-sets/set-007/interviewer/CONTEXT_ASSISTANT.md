# set-007 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() return and in what order does it compute things?

It loads items.csv into a dict keyed by lower-cased item id and responses.jsonl into a list, calls `scoring.grade` to build a per-response dict, `scoring.model_stats` to aggregate per model, and `reports.leaderboard` to rank the models. The report has `responses`, `models` and `leaderboard` keys.

### 2. What does ANSWER_TAG match?

Case-insensitive `answer:` followed by optional whitespace, an optional `(`, one letter A-D (captured) and an optional `)`. `findall` returns the captured letters in order of appearance.

### 3. How is the flags value for one response produced?

`grade` calls `parse_output(resp.output)` with no second argument and stores the returned flags object in that response's row. parse_output appends `no_answer` or `multiple_answers` to the flags it is working with.

### 4. What is by_category, exactly?

A `collections.Counter` created per model in `model_stats`. It is filled from the rows where `correct` is True and then converted to a plain dict sorted by key.

### 5. How are latency strings like "930" handled?

`load_responses` passes `latency_ms` through `_clean` (str + strip) and then `int()`, so both numbers and numeric strings become ints.

### 6. What does leaderboard() sort on?

It sorts `stats.items()` (model name, stats dict) with a tuple key built from the stats and the name, and returns just the model names in that order.
