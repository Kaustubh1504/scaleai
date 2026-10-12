# 24. Read an ugly CSV export

Customers upload contact lists and vendor timesheets to the platform as CSV.
They come out of Excel, Google Sheets, a German ERP and someone's Perl script,
so "CSV" means: maybe a UTF-8 BOM, maybe `;` or tabs instead of commas,
headers like `" Email Address "`, quoted cells with commas and line breaks,
and blank lines everywhere. You're writing the one reader every importer uses.

## Input

Sample files (absolute paths in `problem_api`):

| constant | what's ugly about it |
|---|---|
| `CONTACTS_BOM` | UTF-8 BOM, CRLF line endings, a quoted comma, a quoted newline, blank and whitespace-only lines |
| `VENDOR_SEMICOLON` | `;`-delimited, decimal commas (`7,5`), a quoted `;` |
| `ANNOTATORS_TSV` | tab-delimited |
| `DUP_HEADERS` | `Score,score, SCORE ,Notes,,#` |
| `LATIN1_EXPORT` | Latin-1 bytes, not UTF-8 |
| `SINGLE_COLUMN` | one column, so no delimiter anywhere |

```
 Email Address ,Full Name,Sign-up Date (UTC),Notes
ana@example.com , Ana Lima ,2024-03-01,"Prefers email, not phone"

bo@example.com,Bo Chen,2024-03-02,"Line one
line two"
```

## Setup

```python
from problem_api import ALL_FILES, CONTACTS_BOM, DUP_HEADERS  # absolute pathlib.Paths
print(CONTACTS_BOM.read_bytes()[:200])
```

Every constant in the table above is a `pathlib.Path`; `ALL_FILES` lists all six.
The `if __name__ == "__main__":` block is what the Run button executes: print
the first raw lines (`repr` of the bytes) of each file there before parsing.

## Your task

Your module must define:

* `class CsvFormatError(Exception)`: raised for undecodable or malformed files.
* `normalize_header(name: str) -> str`
* `read_csv(path: str | os.PathLike) -> list[dict[str, str]]`

**Decoding**
* Decode as UTF-8, dropping a leading BOM (`utf-8-sig`). If the bytes are not
  valid UTF-8, raise `CsvFormatError` (don't guess Latin-1: silently wrong
  names are worse than a clear rejection).

**Delimiter** (one of `,` `;` `\t`)
* You may use `csv.Sniffer().sniff(sample, delimiters=",;\t")` on the first
  4096 characters. If it raises `csv.Error`, fall back to the **header rule**:
  count each candidate in the first non-blank line; the most frequent wins;
  ties and zero counts go to `,` (then `;`, then tab). Every test file is one
  where both approaches agree, so the header rule alone is also fine.

**Parsing**
* Use the `csv` module: quoted fields may contain the delimiter, `""` and
  newlines. Keep embedded newlines in the value.
* A record is **blank** if every field is empty after stripping (this
  includes empty lines). Blank records are skipped everywhere.
* The first non-blank record is the header. No header (empty file) → `[]`.

**Headers**: `normalize_header(name)`: strip, lowercase, replace each run of
characters outside `[a-z0-9]` with one `_`, strip leading/trailing `_`.
`" Email Address "` → `"email_address"`, `"Sign-up Date (UTC)"` → `"sign_up_date_utc"`.
* In `read_csv`, a header that normalizes to `""` becomes `column_<n>` (1-based
  position). The 2nd, 3rd, ... occurrence of a name gets `_2`, `_3`, ...
  (you may assume this never collides with another header).

**Rows**
* One dict per data record, keys in header order, every value stripped.
* A record with fewer fields than the header is padded with `""`. Extra fields
  are fine if they're blank (trailing delimiters); a non-blank extra field
  raises `CsvFormatError`.

## Example

```python
read_csv(CONTACTS_BOM)[0]
# {"email_address": "ana@example.com", "full_name": "Ana Lima",
#  "sign_up_date_utc": "2024-03-01", "notes": "Prefers email, not phone"}
read_csv(DUP_HEADERS)[0].keys()
# score, score_2, score_3, notes, column_5, column_6
```

## Constraints

* Standard library only (`csv`, `io`, `re`). No pandas.
* Values stay strings: `"7,5"` is not your problem to convert here.

<details><summary>Hint 1</summary>

Read the bytes and decode with `"utf-8-sig"`, turning `UnicodeDecodeError` into
`CsvFormatError`. Feed the text to `csv.reader` through `io.StringIO(text, newline="")`:
it handles `\r\n` and quoted newlines for you.
</details>

<details><summary>Hint 2</summary>

Look at the raw bytes first. You'll see the `\xef\xbb\xbf`, the `\r\n` and the quotes. `csv.Sniffer` gives up
on the contacts file (blank lines and a quoted newline), so the fallback matters.
</details>

## Follow-up (talk it through)

* A customer insists their file is fine, but it's Windows-1252. Would you
  auto-detect encodings? What's the risk, and what would you show the user?
* The file is 4 GB. What in your reader has to change?
* Why normalize headers at all instead of mapping exact strings?
