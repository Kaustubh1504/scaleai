# set-013 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

`load_registry` builds a set of normalised annotator ids from annotators.csv. `load_submissions` returns `(valid, rejected)`. build_report then builds one `AnnotatorReport` per annotator with valid submissions, counts fast ones with `timing.is_fast`, calls `flag_speeders`, and adds `copying` flags from `copying.copy_tasks`.

### 2. Which rows does load_submissions skip before parsing timestamps?

Rows whose annotator id (as computed in that function) is not in the registry set. Those rows are skipped without being parsed or recorded anywhere.

### 3. When does parse_submission raise?

`parse_time` raises ValueError if a timestamp matches none of the three formats in `TIME_FORMATS`, and parse_submission raises ValueError itself when `submitted_at` is earlier than `started_at`.

### 4. How is fast_ratio computed?

It is a property on `AnnotatorReport` in models.py: `fast / submissions`, rounded to 3 decimals, or 0.0 if there are no submissions. `fast` is the count of submissions for which `is_fast` returned True.

### 5. How does copy_tasks group answers?

It groups submissions by `(task_id, norm_answer(answer))`. For each group it builds `who` from the annotator ids, and when `who` has two or more entries those annotators are added to that task's set. It returns task id → sorted names, with tasks sorted.

### 6. Which annotators appear in the report?

Only annotators who have at least one valid (non-rejected) submission, since table rows are created while iterating over valid submissions. They are listed in sorted id order.
