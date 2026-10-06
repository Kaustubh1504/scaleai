# set-026 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do, step by step?

It loads projects.json, reads every batch CSV whose stem is a project (`load_annotations`), resolves each task (`consensus.resolve`), builds the per-annotator table (`agreement.agreement_table`), counts agreed labels per project and overall (`label_breakdown`), and builds the team summary from teams.csv plus each annotator's vote count.

### 2. What does read_rows return?

A list of dicts, one per CSV data row. Each column name is passed through `clean()` and lower-cased, and each cell is trimmed. It is used for the batch files and for teams.csv.

### 3. How does a skip row flow through the code?

The loader keeps it as an Annotation with label 'skip'; `Annotation.skipped` is True for it. `resolve` leaves skips out of a task's labels but still records the task's project, and `votes_by_annotator` leaves them out. In `agreement_table`, a skip increments that annotator's `skips` counter.

### 4. Where does a task's project come from?

From the batch file name: `load_annotations` passes `norm_id(path.stem)` to `read_batch`, which stamps it on each Annotation. `resolve` remembers the last project seen for each task id.

### 5. How is the label breakdown built?

`label_breakdown` loops over project ids in sorted order, filters results to that project, and calls `count_labels(rows)` for the per-project dict and `count_labels(rows, overall)` to add to the overall Counter.

### 6. What does load_teams do with each roster row?

It reads rows with `read_rows`, takes `row.get("annotator_id")` and `row.get("team")`, normalises both with `norm_id`, and keeps the row only if the annotator id is non-empty. The result maps annotator id to team.

### 7. Which annotators appear in the annotators table?

Every annotator id that appears in the deduped annotations, whether the rows are votes or skips, sorted by id.
