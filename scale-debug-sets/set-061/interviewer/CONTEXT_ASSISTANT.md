# set-061 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() call, in order?

`load_active_annotators` returns sorted active ids, `load_submissions` reads and filters the log, `task_medians` and `rush_stats` build the timing numbers, `shared_answer_counts` builds the copying counts, and then each active annotator gets a row with `flags_for`. The summary is built from those rows, except `worst_rusher`, which is given the `rush` dict.

### 2. Which submissions does load_submissions drop?

Rows whose normalised annotator id isn't in the active list, and rows whose parsed `submitted_at` is before `BATCH_START` (2026-04-01). Blank answers and blank durations are kept; a blank duration becomes `None`.

### 3. What order are the keys in the dict returned by rush_stats?

It is a defaultdict filled while walking the submissions in file order, so keys appear in the order each annotator's first timed submission appears. Annotators with no timed submissions are not in it.

### 4. What does has_twin receive as same_task?

The full list of counted submissions for that task, in file order, built in `shared_answer_counts`. That list includes the submission being checked.

### 5. How does answer_key normalise text?

It strips, lower-cases, replaces runs of whitespace with one space, then strips trailing `.` and `!` characters and any whitespace left behind. A blank answer gives an empty key.

### 6. How is a task median computed when a task has an even number of timed submissions?

`median` sorts the values, takes `mid = len // 2`, and for an even count returns the sum of the two middle values divided by 2.
