# set-022 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, step by step?

It loads thresholds, predictions (via load_predictions, which reads the CSV and calls latest_per_prediction) and reviewers. Then route_all makes one Decision per prediction, build_queue filters and sorts the queue, assign hands items to reviewers, and summarize builds the summary.

### 2. What does latest_per_prediction return?

A list of Prediction objects sorted by pred_id. It walks the rows in file order, keeps one entry per dict key, and replaces the stored row when the new row's created_at is >= the stored one.

### 3. What type is Decision.route?

A member of the `Route` Enum in models.py (`Route.AUTO` or `Route.HUMAN`), a plain Enum whose values are the strings 'auto' and 'human'. The report converts it with `.value`.

### 4. How are thresholds loaded?

load_thresholds reads `default`, the `task_types` map (keys trimmed and lower-cased, values converted with float()) and `always_human_flags` into a set. Thresholds.for_task looks the task type up in that map.

### 5. In what order does route_one check things?

Flags in always_human first, then a missing confidence, then the confidence compared with the threshold for the task type.

### 6. How does assign treat inactive reviewers and capacity?

It only uses reviewers with active True. It tracks remaining capacity per reviewer, filters candidates by language and remaining > 0, and asks pick_reviewer to choose. Items with no candidate go to backlog in queue order.

### 7. How does summarize compute per-type counts?

It sorts the decisions into `ordered`, runs itertools.groupby on task_type, and for each group counts human routes, auto = group size minus human, and human_rate rounded to 3 decimals. The result is stored in a dict keyed by task type.
