# set-024 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, in order?

load_config and load_items, then clean_items (unlabeled, then excluded, else usable), dedupe on the usable rows, assign by document, val_sample on the val rows and split_stats over train, val and test in that order.

### 2. How does dedupe group rows?

text_key lower-cases the text and joins its whitespace-split words with single spaces. Rows with the same key form a group, pick_keeper chooses one per group, and the others' ids are returned sorted as duplicates.

### 3. How is a document's split decided?

assign calls split_for once per doc id (cached in doc_splits). split_for returns test for pinned docs, otherwise uses bucket_for, which is md5 of the doc id as an integer mod 100.

### 4. What does load_config return?

A dict with pinned_test_docs and exclude_tags as sets (parsed with split_list from ';'-separated strings) and val_cap_per_label as an int.

### 5. What is Item.tokens?

A property: the number of whitespace-separated words in the cleaned text.

### 6. How are label counts per split built?

split_stats calls stats.tally with a generator of labels for each split's members, then sorts the resulting dict by label.

### 7. Which rows does val_sample see?

Only by_split['val']. It sorts them by item_id and appends ids to a per-label list while the list is under the cap.
