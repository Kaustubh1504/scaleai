# Part 1: Ticket upload (about 20 minutes)

Customers send us ticket exports as CSV files. Build an endpoint that accepts a
file, validates every row, converts the good rows to JSON, saves the result
locally, and reports the bad rows.

## Input format

UTF-8 CSV (a leading BOM is allowed) with a header row. The header must contain
these columns, in any order; extra columns are ignored:

| column | rule (applied after stripping surrounding whitespace) |
|---|---|
| `ticket_id` | non-empty; not already used by an earlier **valid** row in the same file |
| `customer_email` | matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` |
| `subject` | non-empty |
| `body` | non-empty |
| `created_at` | `datetime.fromisoformat(value.replace("Z", "+00:00"))` succeeds |

Quoted fields may contain commas and newlines. Completely blank lines are
skipped and not counted.

## `POST /uploads`

Multipart form upload with the file in the field named `file`.

* A row whose number of values differs from the header's is invalid
  (`field: null`).
* Otherwise the row is checked against the rules in the table **in table
  order**; the first rule that fails is the row's error.
* Valid rows are stored with exactly the five fields above, as strings, with
  surrounding whitespace stripped.

Success: **201**

```json
{
  "upload_id": "<string>",
  "filename": "tickets.csv",
  "total_rows": 18,
  "valid_rows": 9,
  "invalid_rows": 9,
  "errors": [{"row": 6, "field": "customer_email", "message": "<any text>"}]
}
```

`row` is the 1-based index of the data row (header excluded, blank lines not
counted). `errors` is in row order with one entry per invalid row.

Errors:

| situation | status |
|---|---|
| file name does not end in `.csv` (case-insensitive) | 415 |
| file is empty or has no header row | 400 |
| header is missing a required column | 400 |
| file is not valid UTF-8 | 400 |
| no `file` field | 422 |

Error bodies use FastAPI's `{"detail": "..."}` shape. A header-only file is a
valid upload with zero rows.

## Storage

Save each upload as `<storage_dir>/uploads/<upload_id>.json`, containing the
response object above plus `"tickets": [ ...valid rows in file order... ]`.

## `GET /uploads/{upload_id}`

**200** with the saved object (including `tickets`), or **404** if the upload
does not exist.

## Constraints

* Keep the `create_app(storage_dir, llm, clock, max_concurrency)` signature in
  `app/main.py`; write files only under `storage_dir`.
* Write tests for your work.
