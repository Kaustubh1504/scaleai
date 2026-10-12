# M2. Customer data import

Enterprise customers upload their user lists as CSV exports from whatever tool
they use: Excel, a CRM, a script someone wrote in 2015. The import job must
turn each upload into clean, deduplicated customer records, enrich them from
the company directory API, and survive being killed halfway through a big file.

## Input

`data/customers.csv` (`SAMPLE_CSV` in `problem_api`) is a typical upload:

```
﻿Customer ID; Full Name ;E-Mail;Website;Seats;Last Updated;Notes
C001;Ada  Lovelace;ADA@Acme.io;https://www.acme.io/;25;2024-03-01;renewal in Q3
C004;Linus;linus@kernel.example;kernel.example;1,200;2024-02-01;
C001;Ada Lovelace;ada@acme.io;acme.io;30;2024-04-15;seats bumped
C009;Edsger Dijkstra;edsger@unknown-co.example;;7;2024-03-05
```

## Part 1: clean the upload (about 20 minutes)

### Setup

```python
from problem_api import API_KEY, SAMPLE_CSV, make_api   # SAMPLE_CSV is a pathlib.Path
raw = SAMPLE_CSV.read_bytes()                           # Part 2: http = make_api().client()
```

Your file starts empty; the `if __name__ == "__main__":` block is what the Run button executes (print the raw lines before parsing anything).

### Contract (Part 1)

* `class SchemaError(ValueError)` — a required column is missing.
* `@dataclass class CleanResult` — fields `rows: list[dict]` (good records) and `errors: list[dict]` (each `{"line": int, "reason": str, "customer_id": str | None}`).
* `clean_customers(raw: bytes) -> CleanResult`.

**Reading**

* Decode as UTF-8 and drop a leading BOM.
* The delimiter is whichever of `,` `;` `\t` `|` occurs most often in the
  first line (tie: earliest in that list). Standard CSV quoting applies.
* **Headers**: strip, lowercase, replace each run of non-alphanumeric characters
  with `_`, trim `_` from the ends (`" E-Mail "` → `e_mail`). Then map aliases
  (unknown columns are ignored; if two headers map to one field, the first wins):

  | field | accepted headers |
  |---|---|
  | `customer_id` | `customer_id`, `id`, `customer`, `cust_id` |
  | `name` | `name`, `full_name`, `customer_name` |
  | `email` | `email`, `e_mail`, `email_address`, `mail` |
  | `company_domain` | `company_domain`, `domain`, `website`, `company_website` |
  | `seats` | `seats`, `seat_count`, `licenses` |
  | `updated_at` | `updated_at`, `last_updated`, `updated`, `modified` |

  `customer_id`, `email` and `updated_at` are required: if any is missing raise
  `SchemaError`. `name`, `company_domain`, `seats` may be absent (treated as empty).
* A record whose fields are all empty/whitespace (e.g. a blank line) is skipped silently.
* `line` is the 1-based line of the file where the record starts (the header is line 1).

**Validating** (strip every value first; report the **first** failing check):

1. More fields than the header and any extra one is non-empty → `too_many_fields`
   (empty extras, like a trailing `;;`, are fine). Fewer fields: missing ones are empty.
2. Empty `customer_id` → `missing_customer_id`.
3. `email`, lowercased, must match `[^@\s]+@[^@\s]+\.[^@\s]+` → else `invalid_email`.
4. `updated_at` must be a real date written `YYYY-MM-DD` → else `invalid_updated_at`.
5. `seats` empty → `None`; ASCII digits → `int`; anything else (`1,200`, `-1`, `n/a`) → `invalid_seats`.

**A good row** has exactly these keys, e.g.
`{"customer_id": "C001", "name": "Ada Lovelace", "email": "ada@acme.io", "domain": "acme.io", "seats": 30, "updated_at": "2024-04-15"}`.

* `name`: internal whitespace collapsed to single spaces; empty → `None`.
* `domain`: `company_domain` lowercased, with a leading `https://` or `http://`,
  then a leading `www.`, removed and everything from the first `/` dropped
  (`https://www.Acme.io/about` → `acme.io`). If that is empty, use the part of
  the email after `@`.

**Duplicates**: when several good rows share a `customer_id`, keep the one with
the latest `updated_at`; on a tie keep the **later** line. Each discarded row is
an error with reason `duplicate`.

**Output order**: `rows` in order of the kept row's line; `errors` sorted by
`line` (`customer_id` is the stripped value, or `None` if empty).

<!-- part 2 -->

## Part 2: enrich from the company directory (about 20 minutes)

`GET /v1/companies/{domain}` with header `X-API-Key: <key>`:

```json
{"domain": "acme.io", "name": "Acme Corp", "industry": "Manufacturing", "employee_count": 1200}
```

**404** means the directory doesn't know the company. A bad key is **401**.

### Contract (Part 2)

* `class ApiError(Exception)` — `ApiError(status: int, path: str, message: str = "")`; attributes `.status`, `.path` (e.g. `"/v1/companies/acme.io"`).
* `class CompanyCache` — `__init__(self, clock, ttl_s: float = 300.0, negative_ttl_s: float = 60.0)`; `clock.time()` gives now.
* `CompanyCache.get(domain: str) -> tuple[bool, dict | None]` — `(hit, company)`; a miss is `(False, None)`.
* `CompanyCache.put(domain: str, company: dict | None) -> None` — `None` means "not found" and is cacheable.
* `enrich_rows(rows: list[dict], http: httpx.Client, api_key: str, cache: CompanyCache) -> list[dict]`.
* Free-mail domains: `gmail.com`, `yahoo.com`, `outlook.com`, `hotmail.com`, `icloud.com` (define this set yourself).

Tests pass a `kit.FakeClock` and `make_api({...}).client()`.

* Each output row is a **new** dict: the input row plus
  `company_name`, `industry`, `employees` (from `name`, `industry`,
  `employee_count`) and `enrichment`, in the same order as `rows`.
* `enrichment` is `"enriched"`, `"not_found"` (a 404: the three company fields
  are `None`) or `"skipped"`.
* Rows whose `domain` is one of the free-mail providers above are `"skipped"`
  (company fields `None`), with no request.
* **Cache**: look the domain up in `cache` first; on a miss, call the API and
  `put` the result (a 404 is stored as `None`). An entry stored at time `t` is a
  hit while `clock.time() < t + ttl`, where `ttl` is `ttl_s` for a company and
  `negative_ttl_s` for `None`. Expired entries are misses.
* Any other non-2xx response raises `ApiError` (status, path).

<!-- part 3 -->

## Part 3: big files, flaky API, crashes (about 20 minutes)

### Contract (Part 3)

* `run_import(csv_path: str | Path, out_dir: str | Path, http: httpx.Client, api_key: str, *, max_workers: int = 4) -> dict` — writes the files below and returns the counts.

* Clean the file (Part 1), then look up each **distinct** non-free-mail domain
  **at most once**, using a `ThreadPoolExecutor` with at most `max_workers`
  requests in flight.
* A lookup **fails** on any non-2xx except 404, any `httpx.TransportError`, or a
  2xx whose body is not valid JSON. A failure is not fatal: those rows get
  `enrichment: "failed"` (company fields `None`) and the import carries on.
* **Outputs** in `out_dir` (create it if needed):
  * `customers.jsonl`: one JSON object per good row (Part 2 shape), in Part 1 order;
  * `errors.jsonl`: one JSON object per Part 1 error, in order;
  * `checkpoint.json`: a JSON object `{domain: {"company_name", "industry",
    "employees"} | null}` holding every lookup that **succeeded** (found or 404).
    Rewrite it after each successful lookup.
* **Every** write is atomic: write a temporary file in `out_dir`, then
  `os.replace` it onto the final name. After a successful run `out_dir` holds
  only those three files.
* **Resume**: if `checkpoint.json` exists, its domains are not requested again.
  Failed lookups are not checkpointed, so the next run retries them.
* Anything else that goes wrong (e.g. the process is killed) propagates; the
  checkpoint must still be valid JSON afterwards.
* Return `{"rows", "errors", "enriched", "not_found", "skipped", "failed"}` (counts).

## Constraints

* HTTP only (don't read `api.companies`). Use the clock for cache time.
* Part 3 tests use a real per-request latency of 20 ms; keep it concurrent.

<details><summary>Hint 1</summary>

Use `csv.reader` over an `io.StringIO` (with `newline=""`). Its `line_num`
is the last line read so far, so note it *before* each `next()`: the record starts one line later.
</details>

<details><summary>Hint 2</summary>

Dedupe domains *before* submitting work (`dict.fromkeys` keeps the order).
Workers return results; one lock guards the shared checkpoint dict and its file.
</details>

## Discussion (talk it through)

* Your checkpoint is per domain. What would you checkpoint for a 50 GB file
  where even cleaning can't be repeated cheaply (byte offsets? row batches?)
* "Latest `updated_at` wins" vs "last row wins" vs "merge non-empty fields": which
  would you pick for customer data, and who should decide?
* How do you pick `max_workers` against an API you don't own? What changes if
  the directory starts rate limiting, or if two import jobs run at once?
