# set-002 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the pipeline inside build_report()?

`load_annotators` builds the registry, `load_tasks` returns task ids plus the gold labels, and `load_annotations` reads the CSV, keeps only rows from active registry annotators and dedupes them. `gold.quality_table` then computes accuracy, `voting.mark_blocked` sets the blocked flags, `voting.resolve` builds consensus for non-gold tasks, and `reports.summarize` builds the summary.

### 2. What does norm_annotator do, and where is it called?

It is `clean(value).lower()`, defined in `utils.py`. In this repo it is called from `loader.load_annotators` when building the registry keys.

### 3. How does latest_submissions decide which duplicate to keep?

It keys rows by `(task_id, annotator_id)` and replaces the stored row whenever the new row's `submitted_at` is `>=` the stored one. So the latest timestamp wins, and on equal timestamps the row later in the file wins. The output keeps the order in which each key was first seen.

### 4. What accuracy does quality_table give an annotator who answered no gold tasks?

They don't appear in `rates` (which only has annotators with at least one gold answer), so the module-level `PRIOR` of 0.5 is used, with `gold_answered` = 0. Only active registry annotators get a row at all.

### 5. In resolve(), whose votes count and how much does each weigh?

`weights` is built from table rows that aren't blocked, with weight = that annotator's accuracy. Votes from anyone not in `weights` are dropped. Gold tasks are skipped entirely, and a task with fewer than `MIN_VOTES` (2) counting votes gets `needs_more_votes`.

### 6. How is confidence computed?

The winning label's total weight divided by the sum of all label totals for that task, rounded to 3 decimals.

### 7. How is most_disputed chosen?

`summarize` takes the minimum over resolved results by `(confidence, task_id)`, so the lowest confidence wins and ties go to the lower task id.
