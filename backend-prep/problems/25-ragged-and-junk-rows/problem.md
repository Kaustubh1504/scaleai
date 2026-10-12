# 25. Ragged rows, repeated headers and footers

Finance sends the monthly annotator payout file. It's two exports glued
together with `cat`: each starts with `#` comment lines and a header, and ends
with a `TOTAL` line and an `Exported N rows` line. Some rows are ragged, some
are missing the amount. You need the good rows **and** an error report that
points finance at the exact line in the file they have open in their editor.

## Input

`problem_api.PAYOUTS` (and `problem_api.REQUIRED = ["annotator_id", "amount_usd"]`):

```
 1  # Payout export v3, generated 2024-06-01
 2  # columns: annotator_id,task_id,hours,amount_usd,note
 3  annotator_id,task_id,hours,amount_usd,note
 4  ann_01,t-100,2.5,37.50,
 5  ann_02,t-101,1.0,15.00,"QA pass, no issues"
 6  ann_03,t-102,3.0,45.00,"Reviewer said:
 7  ""redo spans 4-7""
 8  then approved"
 9  ann_04,t-103,2.0,30.00
10  ann_05,t-104,1.5,22.50,ok,EXTRA
...
16  annotator_id,task_id,hours,amount_usd,note
...
```

UTF-8 (a BOM may be present), comma-delimited, standard CSV quoting.
Quotes are always balanced.

## Setup

```python
from problem_api import PAYOUTS, REQUIRED   # PAYOUTS is an absolute pathlib.Path
```

The `if __name__ == "__main__":` block is what the Run button executes: print
the file with line numbers there, and what `csv.reader` makes of each record.

## Your task

Your module must define:

* `class SchemaError(Exception)`: constructor `SchemaError(missing)`; attribute
  `.missing: list[str]` (required columns absent from the header, in `required` order).
* `@dataclass class Result`: fields `rows: list[dict[str, str]]` and
  `errors: list[dict]` (each `{"line": int, "reason": str}`).
* `load_rows(path: str | os.PathLike, required: list[str]) -> Result`

Go through the file record by record (a record may span several physical
lines because of quoted newlines). For each record, in this order:

1. **Blank** (every field empty after stripping): skip.
2. **Comment** (first field, stripped, starts with `#`): skip.
3. The first record that survives 1–2 is the **header** (names stripped).
   If any `required` name is not in it, raise `SchemaError` with `.missing`.
   A file with no header at all raises `SchemaError` with every required name.
4. **Repeated header** (stripped values equal the header): skip.
5. **Footer** (first field, stripped, matches `TOTAL` or `Exported <digits> row(s)`,
   case-insensitive, whole field): skip.
6. Field count ≠ header length → error `"too_many_fields"` / `"too_few_fields"`.
7. Any required column empty after stripping → error `"missing_required"`.
8. Otherwise it's a row: `dict(zip(header, stripped values))`.

* Steps 1, 2, 4 and 5 are **silent**: they are not errors.
* At most one error per record. `errors` and `rows` are in file order.
* `line` is the **1-based physical line where the record starts**. Lines inside
  a multi-line quoted field count, so a record after a 3-line record is 3 lines later.

## Example

```python
res = load_rows(PAYOUTS, REQUIRED)
res.rows[2]["note"]  # 'Reviewer said:\n"redo spans 4-7"\nthen approved'
res.errors[:2]       # [{"line": 9, "reason": "too_few_fields"},
                     #  {"line": 10, "reason": "too_many_fields"}]
```

## Constraints

* Use the `csv` module; don't split lines on `,` yourself (quoted commas and newlines).
* Don't count lines by hand-parsing quotes: let the reader tell you.

<details><summary>Hint 1</summary>

Open with `newline=""` and `encoding="utf-8-sig"`. `reader.line_num` is the number of physical lines read so far, i.e. the line where
the record you just got **ends**. So the record started at
`previous line_num + 1`.
</details>

<details><summary>Hint 2</summary>

`enumerate(reader, start=1)` is the classic bug here: it counts records, not
lines, and drifts by two after `ann_03`'s note.
</details>

## Follow-up (talk it through)

* Should a file with 40% bad rows be loaded at all? Where would you put the threshold, and who decides?
* The footer says `Exported 6 rows`. How could you use it to detect a truncated export?
* How would you hand the error report back to finance so they can fix and re-upload?
