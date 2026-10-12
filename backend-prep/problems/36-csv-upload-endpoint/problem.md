# 36. CSV upload endpoint with row validation

Vendors send labelled annotation batches as spreadsheets exported to CSV.
Ops wants to upload a file and get back, right away, **which rows are bad and
why**, while the good rows get stored for the ingestion job. Build that
endpoint. The files are messy: Excel BOMs, stray whitespace, mixed-case
labels, broken timestamps, duplicate tasks.

## Input

`POST /uploads` is a `multipart/form-data` request with one file field named
**`file`**:

```
task_id,annotator_email,label,submitted_at,notes
t-001,Ana@Example.com,positive,2024-05-01T10:00:00Z,looks fine
t-002,ben@example.com, Neutral ,2024-05-01T12:30:00+02:00,
t-003,not-an-email,negative,2024-05-01T11:00:00Z,
```

Required columns: `task_id`, `annotator_email`, `label`, `submitted_at`.
Extra columns (like `notes`) are allowed and ignored.

## Setup

```python
from problem_api import SAMPLE_CSV          # bytes of a messy 6-row upload
client = TestClient(create_app(tmp_path))   # how the tests build your app
client.post("/uploads", files={"file": ("batch.csv", SAMPLE_CSV, "text/csv")})
```

Your file starts empty. An `if __name__ == "__main__":` block is what the Run
button executes: use it to print the sample and poke your endpoints.

## Your task

Write a FastAPI app in your file exposing:

* `create_app(storage_dir: str | Path) -> FastAPI`: a factory; all state lives under `storage_dir`.
* `POST /uploads` (multipart field `file`) → `201` summary, or `422` / `415` / `400` as below.
* `GET /uploads/{upload_id}` → `200` stored object, `404` unknown id.

**File-level checks** (in this order; nothing is stored when one fails;
errors are `{"detail": "<message>"}`, e.g. via `HTTPException`):

| status | when |
|---|---|
| 422 | no `file` field (FastAPI's default validation error) |
| 415 | the filename doesn't end in `.csv` (case-insensitive: `.CSV` is fine) |
| 400 | the bytes aren't valid UTF-8 (a leading UTF-8 BOM is allowed and stripped) |
| 400 | no header: the file has no non-blank line |
| 400 | required columns missing: `detail` names every missing column |

Header names are compared after stripping whitespace and lower-casing.
Completely empty lines are skipped everywhere and are not rows. Rows are
numbered `1, 2, ...` starting at the first data row after the header.

**Row rules**: check in this order and report only the **first** failure per
row, as `{"row": n, "field": ..., "message": ...}`. Values are stripped of
surrounding whitespace first.

| # | field | rule | message |
|---|---|---|---|
| 1 | `null` | row has as many fields as the header | `expected {header fields} fields, got {row fields}`, e.g. `expected 5 fields, got 3` |
| 2 | `task_id` | not empty | `required` |
| 3 | `task_id` | not used by an **earlier valid** row | `duplicate task_id` |
| 4 | `annotator_email` | not empty | `required` |
| 5 | `annotator_email` | matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` | `invalid email` |
| 6 | `label` | not empty | `required` |
| 7 | `label` | lower-cased, one of `negative`, `neutral`, `positive` | `must be one of: negative, neutral, positive` |
| 8 | `submitted_at` | not empty | `required` |
| 9 | `submitted_at` | `datetime.fromisoformat` accepts it (after turning a trailing `Z` into `+00:00`) **and** it has a UTC offset | `invalid timestamp` |

**Success** is `201`:

```json
{"upload_id": "…", "filename": "batch.csv", "total_rows": 6, "valid_rows": 2,
 "invalid_rows": 4, "errors": [{"row": 3, "field": "annotator_email", "message": "invalid email"}, …]}
```

* `errors` is ordered by row. A header-only file is a success with 0 rows.
* `upload_id` is a new unique id, safe to use as a filename (e.g. `uuid4().hex`).
* Valid rows are stored normalised, in file order, with only the four
  required keys: `task_id` stripped, `annotator_email` and `label`
  lower-cased, `submitted_at` converted to UTC as `"2024-05-01T10:30:00Z"`.
* Write `storage_dir/uploads/<upload_id>.json` (create the directories)
  containing the POST body plus `"rows": [...]`. Leave no temp files behind,
  and store nothing for a request that fails a file-level check.
* `GET /uploads/{upload_id}` returns that stored object (200), read from disk
  so a fresh `create_app` over the same `storage_dir` still finds it. Unknown
  id → 404.

## Example

Uploading `SAMPLE_CSV` from `problem_api` as `batch.csv` gives
`total_rows: 6, valid_rows: 2`, errors on rows 3 (`invalid email`),
4 (`duplicate task_id`), 5 (label), 6 (`invalid timestamp`), and stored row 2
is `{"task_id": "t-002", "annotator_email": "ben@example.com",
"label": "neutral", "submitted_at": "2024-05-01T10:30:00Z"}`.

## Constraints

* No module-level state: everything lives under `storage_dir`.
* Use the `csv` module (quoted fields may contain commas), not `line.split(",")`.

<details><summary>Hint 1</summary>

Declare the parameter as an `UploadFile` taken from `File(...)`, read its bytes,
and decode with the `utf-8-sig` codec (it strips a BOM). A failed decode raises
`UnicodeDecodeError`.
</details>

<details><summary>Hint 2</summary>

Use `csv.reader(io.StringIO(text))`, not `DictReader`: you need to see rows
with the wrong number of fields. Skip rows that are `[]` (blank lines). Map
each required column name to its index in the header once.
</details>

<details><summary>Hint 3</summary>

Write the JSON to `<id>.json.tmp` and `os.replace` it into place so a crash
never leaves a half-written upload. Before opening `<id>.json` in GET, check
the id looks like one you generate, so `GET /uploads/..%2Fsecret` can't wander.
</details>

## Follow-up (talk it through)

* The file is 2 GB. What changes (streaming parse, size limits, background job)?
* Should one bad row reject the whole upload? Who decides, and how would the API express both modes?
* The same file gets uploaded twice. How would you make uploads idempotent?
