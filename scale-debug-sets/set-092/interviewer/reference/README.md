# Embedding Index Sync

Help-centre documents live in a CSV export. This tool keeps a remote vector index in step
with that export: it lists what the index already holds, sends only new or changed
documents to the embeddings endpoint (in concurrent batches, with retries), and reports
which index entries should be removed.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real embeddings API and vector index (rate limits, 5xx errors, paginated listings). It is
test infrastructure, so leave it alone. `tests/harness.py` is also test infrastructure.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: run settings. Keys that are present must be used as given; the
  defaults in `config.py` apply only to keys that are **missing**. `as_of` is the run date.
- `data/documents.csv`: `doc_id`, `collection`, `text`, `updated_at`.
- `data/retired.csv`: `doc_id`, `retired_on`, `reason`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Documents

- `doc_id` and `collection`: trim and lower-case. `text`: trim. Rows with blank text are
  dropped.
- `updated_at` is `2026-09-01 10:00`, `09/01/2026 10:00` (month/day/year) or
  `2026-09-01T10:00:00`.
- If a `doc_id` appears more than once, keep the row with the latest `updated_at`; on equal
  timestamps the later row in the file wins.
- A document is **retired** when `retired.csv` lists it with a `retired_on` date on or
  before `as_of`. A blank or later date means it is still active. Retired documents are
  never embedded and never appear in `outcomes`.

### What gets embedded

1. For each collection, list the index with `GET {base_url}/v1/index/<collection>?limit=<page_size>`,
   then keep requesting with `&page_token=<next_page_token>` until `next_page_token` is
   `null`. **Every** page's items count, including the last one.
2. An active document whose index entry has the same `sha1` as its text (SHA-1 of the UTF-8
   text, hex) is `skipped`. Every other active document is embedded.
3. Index entries whose `doc_id` is not an active document go to `to_delete` (sorted).

### Embedding requests

4. Documents to embed are sorted by `(collection, doc_id)` and cut into batches of
   `batch_size` per collection. Batch ids are `<collection>-<n>`, with `n` starting at 0.
5. Each batch is `POST {base_url}/v1/embeddings` with headers
   `Authorization: Bearer <api_key>` and `Content-Type: application/json`, and body:

   ```json
   {
     "model": "<config.model>",
     "dimensions": <config.dimensions>,
     "input": ["<text>", "..."],
     "documents": [{"id": "<doc_id>", "updated_at": "<ISO 8601, e.g. 2026-09-01T10:00:00>"}],
     "metadata": {"batch_id": "<batch id>"}
   }
   ```
6. At most `max_concurrency` embedding requests may be in flight at any moment.
7. HTTP 429, 500, 502, 503 and 504 are transient: retry up to `max_retries` times (at most
   `max_retries + 1` attempts). Before each retry, wait `Retry-After` seconds if the
   response has that header, otherwise `backoff_seconds × 2^attempt` (`attempt` starts at 0).
8. A batch whose final status is not 200 has failed: each of its documents is `failed`,
   and the batch is listed in `failed_batches` with that status. A failed batch must not
   stop the other batches.
9. On 200, `data[i].index` is the position in `input` that `data[i].embedding` belongs to
   (items may come back in any order). Each document in the batch is `embedded`.

### Report

`embedsync.reports.build_report(base_url, api_key)` returns:

- `outcomes`: `doc_id` → `embedded` / `skipped` / `failed`, for every active document;
- `embeddings`: `doc_id` → vector, for embedded documents;
- `to_delete`: from rule 3;
- `summary`:
  - `counts`: number of documents per outcome (`embedded`, `skipped`, `failed`);
  - `failed_batches`: batch id → final HTTP status;
  - `total_tokens`: sum of `usage.total_tokens` over successful responses;
  - `cost_usd`: `total_tokens ÷ 1000 × price_per_1k_tokens`, rounded to 4 decimals.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run a sync against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py` and `tests/harness.py`) or
  anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
