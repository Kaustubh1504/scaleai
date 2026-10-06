# set-056 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, step by step?

`ingest` loads the category registry, then for each CSV in data/feeds (sorted by name) runs `validate_feed(path.stem, read_feed(path), registry)`, collecting accepted records, rejects and a per-source accepted count. `latest_by_sku` merges accepted records, `live_catalog` drops discontinued winners and sorts by SKU, and `summarize` builds the summary.

### 2. What does read_feed yield, and how are header names handled?

It opens the file with csv.DictReader and yields `(reader.line_num, row)`, where `_normalise` maps each key to `clean(key).lower()` and each value to `clean(value)`. `clean` is `(value or '').strip()`.

### 3. In what order does build_record check a row?

SKU (blank -> missing_sku), category lookup in the registry (missing or inactive -> unknown_category), price via parse_price, qty via parse_qty, then updated_at via parse_updated. Each failure raises RowError with a reason, which validate_feed turns into a Reject.

### 4. What does parse_updated accept?

It tries `%Y-%m-%d`, `%m/%d/%Y` and `%Y-%m-%dT%H:%M:%S` in that order on the trimmed text and raises RowError('bad_date') if none match. strptime also rejects impossible dates like 2026-04-31.

### 5. How does latest_by_sku decide between two records for the same SKU?

It walks the accepted records in feed/line order and keeps a dict SKU -> record, replacing the stored record when the comparison on `updated_at` in its `if` succeeds.

### 6. How are top_category and duplicates_removed computed?

top_category is `min` over category codes keyed by `(-stock_value, code)`. duplicates_removed is `len(accepted) - len(winners)`.

### 7. How is the registry's active flag read?

`load_categories` calls `parse_bool(item.get('active', True))`; strings are matched against true/yes/y/1 after strip/lower, anything else goes through bool().
