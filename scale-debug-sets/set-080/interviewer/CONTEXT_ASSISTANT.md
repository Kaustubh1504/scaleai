# set-080 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does ingest() return, and in what order are sources read?

A tuple (per_source, rejected, roster, duplicates). Sources come from sources.json with lower-cased names and are processed in sorted order: vendor_a, vendor_b, vendor_c. Each row goes through check_row, and accepted Records are merged at the end by dedupe.merge.

### 2. How does read_source decide how to read a file?

By suffix: .json goes to read_json_source (json.load of a list), and anything else to read_csv_source (csv.DictReader). Both wrap each row as RawRow(source, row_number_from_1, dict_of_fields).

### 3. What does check_row return?

One of ('rejected', reason), ('inactive', None) or ('ok', Record). Checks run in order: missing email, invalid email, unparseable date, invalid hours, then active.

### 4. What are the first bytes of vendor_a.csv?

EF BB BF, the UTF-8 byte-order mark, followed by the header line `email,name,country,skills,hours_per_week,updated_at,active`. vendor_b.csv starts directly with `name,email,...`.

### 5. Which emails appear in more than one accepted row?

In the source data: ana (vendor_a, vendor_b), cara (vendor_b, vendor_c), gus (twice in vendor_a), kim (vendor_a, vendor_b), mia (vendor_b, vendor_c) and raj (vendor_b, vendor_c). cara's and kim's pairs have identical updated_at values.

### 6. How is the export string produced?

export_roster sorts the roster by email, turns each Contributor dataclass into a dict with vars(), and calls json.dumps with indent=2 and sort_keys=True. The `default` argument handles values json can't encode natively, such as datetime.

### 7. Where are skill_counts and countries computed?

In reports.build_report, with collections.Counter over the merged roster's values: each contributor's skills list for skill_counts, and each contributor's country for countries. Both are returned sorted by key.
