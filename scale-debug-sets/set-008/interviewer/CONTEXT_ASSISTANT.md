# set-008 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

`pipeline.ingest` walks `data/` in file-name order, reads each `.csv`/`.json` with `readers.read_export`, turns each row into a record with `normalize.build_record` (or a rejection entry), and then calls `dedupe.merge_duplicates`. `report.build_report` keeps a fixed set of fields per record and builds the summary Counters.

### 2. What do the rows returned by read_export look like?

A list of dicts keyed by the column names after `str(k).strip().lower()`. Values are left as read: strings from CSV, and strings, numbers or None from JSON.

### 3. How does ingest pick the rejection reason?

Any ValueError raised by build_record is caught, and the reason is the label of the first `(class, label)` pair in the module-level REASONS list that the exception is an instance of.

### 4. Which exception classes exist and how are they related?

`schema.py` defines `RowError(ValueError)` and `MissingField(RowError)`. Plain ValueErrors also come from `float()` in parse_rate.

### 5. How does build_record create a new record?

After the email checks it starts from a copy of `schema.DEFAULTS`, then sets email, vendor, order, updated_at, sources, skills, country and name, and appends to `record["notes"]` when the name or rate is blank.

### 6. In merge_duplicates, which row's fields survive?

Rows are grouped by email. The winner starts as the first row and is replaced by any later row for which `newer(row, winner)` is true. The output is a dict copy of the winner with `skills` and `sources` rebuilt from the whole group. `absorbed` adds group size minus 1.

### 7. What does parse_rate accept?

It strips a leading `$`, divides values ending in `/day` by 8, converts with float(), raises RowError for negatives and rounds to 2 decimals. build_record only calls it when the cleaned rate is non-blank.
