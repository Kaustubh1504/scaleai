# set-048 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does load_samples return and in what order does it apply its rules?

A LoadResult with `samples` (kept Sample objects in file order), `excluded` and `duplicates` (ids). For each row it skips blank labels, then checks `parse_flag(exclude)`, then checks a `seen` set for duplicates, then builds the Sample with normalised ids and a parsed timestamp.

### 2. What does group_labels produce?

A dict of group id → label, built with itertools.groupby over the samples keyed by group_id, calling `majority()` on each run's labels.

### 3. What does strata() return?

A dict of label → sorted list of the group ids whose group label is that label.

### 4. How does split_groups size each split?

Per stratum (labels processed in sorted order) it computes `n_test = n * test_percent // 100` and `n_val = n * val_percent // 100`, then walks three slices of the sorted group list, writing 'test', 'val' and 'train' into one assignment dict.

### 5. What happens to a sample whose group has no entry in the assignment?

build_splits looks it up with `assignment.get(group_id)`; if that is None the sample is skipped and appears in no split.

### 6. Which samples does the cap look at?

Only the train members, sorted by (created_at, sample_id). Val and test lists are passed through unchanged.

### 7. How is label_counts built?

It starts from a zeroed dict over every label in the kept samples, creates a per-split dict from it, and increments by each member's own sample label (not the group label).
