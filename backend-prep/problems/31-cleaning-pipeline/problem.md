# 31. End-to-end cleaning pipeline

Vendors drop a CSV of labeled submissions into a bucket every night. Your job
turns it into a clean JSONL file the payout service loads, plus an error
report the vendor-ops team sends back. It runs on a schedule and gets
re-run by hand when something looks off, so it must be **deterministic**,
**idempotent** and must **never leave half-written outputs** behind.

## Input

`problem_api.SUBMISSIONS_CSV` (look at it raw first):

```
﻿ Submission_ID ,Task_ID,annotator_id, Label ,submitted_at,PAYOUT,notes\r\n
S001,T1,a01,Cat,2024-03-01T10:00:00Z,$1.20,\r\n
 s002 ,T1,A02, dog ,2024-03-01T10:05:00+02:00,1.20,late\r\n
...
```

`problem_api.ANNOTATORS_JSON`: `[{"annotator_id": "A01", "name": "Ada"}, ...]`
(ids may need `strip().upper()` too).

## Setup

```python
from problem_api import ANNOTATORS_JSON, SUBMISSIONS_CSV   # absolute pathlib.Paths
```

The `if __name__ == "__main__":` block is what the Run button executes: print
the CSV's raw lines (`repr` of the bytes) and the annotators JSON there first.

## Your task

Your module must define:

* `@dataclass class Summary`: `int` fields, in this order, `rows_read`,
  `invalid_rows`, `duplicates_dropped`, `conflicts`, `superseded_rows`,
  `unknown_annotator_rows`, `clean_rows` (tests call `dataclasses.asdict` on it).
* `run_pipeline(csv_path: str | os.PathLike, annotators_path: str | os.PathLike, out_dir: str | os.PathLike) -> Summary`

**1. Read.** UTF-8 with an optional BOM. Header names are stripped and
lower-cased; the required columns are `submission_id, task_id, annotator_id,
label, submitted_at, payout` (any order; extra columns ignored). A missing
required column raises `ValueError` and writes nothing. Every cell is stripped;
cells missing from a short row are empty. Rows whose cells are all empty are
skipped and not counted. A row's **line** is `csv.reader`'s `line_num` (header
= line 1; blank lines count; there are no multi-line fields). `rows_read` = rows
not skipped.

**2. Normalize and validate**, field by field in the column order above. An empty
field is reason `missing`. Otherwise:

| field | normalized | else reason |
|---|---|---|
| `submission_id`, `task_id`, `annotator_id` | upper-cased | |
| `label` | lower-cased, must be `cat`, `dog` or `other` | `bad_label` |
| `submitted_at` | ISO 8601 (`Z`, offset, or naive = UTC) or all-digit epoch seconds → `"YYYY-MM-DDTHH:MM:SSZ"` in UTC, fractional seconds dropped | `bad_timestamp` |
| `payout` → `payout_cents` | optional `$`, commas removed, then `\d+(\.\d{1,2})?` dollars → int cents | `bad_payout` |

A row with any error is **invalid** (`invalid_rows`): it gets one `errors.csv`
row per failing field and goes no further.

**3. Dedupe** valid rows by `submission_id`:
* A row whose normalized record equals an earlier one is an exact duplicate:
  dropped silently (`duplicates_dropped`), not in `errors.csv`.
* If an id still has several distinct versions, it is a **conflict**
  (`conflicts` counts ids). Keep the version with the latest `submitted_at`
  instant; on a tie, the one appearing later in the file. Every other version
  is `superseded`: error row `(line of its first occurrence, submission_id,
  superseded)`, counted in `superseded_rows`.

**4. References.** A kept record whose `annotator_id` is not a known annotator
gets error `(line, annotator_id, unknown_annotator)` and is dropped
(`unknown_annotator_rows`). Everything left is clean (`clean_rows`).

**5. Write** into `out_dir` (create it, with parents, if missing), UTF-8, `\n` line endings:
* `clean.jsonl`: one `json.dumps(record)` per line, keys in the order
  `submission_id, task_id, annotator_id, label, submitted_at, payout_cents`,
  sorted by `submission_id`.
* `errors.csv`: header `line,field,reason`, sorted by line, then by field in column order.
* `summary.json`: `json.dumps(asdict(summary), indent=2) + "\n"`.

**Atomically**: write all three to temp files **in `out_dir`**, and only once
all are written, `os.replace` each into place. If anything raises, delete your
temp files and re-raise: the previous outputs stay untouched and nothing else
is left in `out_dir`. Return the `Summary`.

## Example

The sample file gives `Summary(rows_read=19, invalid_rows=6,
duplicates_dropped=1, conflicts=3, superseded_rows=3, unknown_annotator_rows=1,
clean_rows=8)` and an `errors.csv` starting with:

```
line,field,reason
4,label,bad_label
5,submitted_at,bad_timestamp
6,task_id,missing
7,annotator_id,unknown_annotator
```

## Constraints

* Standard library only (no pandas). Money as integer cents, never float.
* Move files into place with `os.replace` (or `Path.replace`); tests patch it.
* Same inputs → byte-identical outputs on every run.

<details><summary>Hint 1</summary>

Structure it as small stages (read rows, normalize, dedupe, check references,
write), each returning plain data, with the counters in one
`Summary`. Build all three file contents in memory, then write.
</details>

<details><summary>Hint 2</summary>

Once timestamps are normalized to `...Z` strings, they sort chronologically,
so the winner is the max by `(submitted_at, line)`.
</details>

<details><summary>Hint 3</summary>

`tempfile.mkstemp(dir=out_dir)` puts the temp file on the same filesystem, so
`os.replace` is an atomic rename. On any exception (even `BaseException`),
unlink the leftovers and re-raise.
</details>

## Follow-up (talk it through)

* Replacing three files one by one isn't atomic as a *set*: a crash between
  the 2nd and 3rd replace leaves mixed outputs. How would you fix that
  (versioned directory + symlink swap, a manifest, a database transaction)?
* The file grows to 20 GB. Which stages can stream and which need state (and
  how much)?
* Should a superseded row be an "error" the vendor sees, or a separate audit log?
