# set-032 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the flow inside build_report()?

It resolves vendor settings from vendors.json, then for each vendor (sorted) loads its file with `load_vendor`, records the row count, and splits rows with `validate.partition`. All accepted rows go to `dedupe.dedupe`, which returns one record per task id, and `summarize` builds the summary from those records.

### 2. How are vendor settings built from the defaults?

`config.vendor_settings` loops over the vendor names, copies `defaults`, calls `update()` on the copy's `label_map` with the vendor's own map, then sets every other key from the vendor entry. The result is keyed by the trimmed, lower-cased name.

### 3. What does read_rows return for a CSV vs. the JSON file?

For `.json` it returns the parsed list of objects. For anything else it returns `list(csv.DictReader(fh))`, so a list of dicts keyed by the header names as they appear in the file.

### 4. What does split_tags do with a list vs. a string?

A list is used as is; a string is trimmed and split on ';'. Each part is trimmed and lower-cased, then a loop removes blank entries and entries starting with `tmp:` from that list.

### 5. How does merge() pick the winning copy?

`max(copies, key=rank)`, where `rank` returns a tuple built from `submitted` and the copy's `priority`. max() keeps the first copy if two have equal keys, and copies are in load order (vendor name, then file order).

### 6. What does tag_counts count exactly?

For each final record it counts each tag once (it iterates over `set(rec.tags)`), so the value is the number of final records carrying the tag.

### 7. Where does the row number in a rejection key come from?

`load_vendor` enumerates the rows from 1 and stores the index in `Record.row`; `Rejection.key` formats it as `vendor:row`.
