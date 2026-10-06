# Embedding Backfill

A nightly job re-embeds knowledge-base documents. It groups documents into batches,
sends the batches to an embeddings service concurrently (with a cap on how many are in
flight), retries transient failures, commits the job, and then reads back the vector index
to check that every accepted document was stored.

The client is built on `asyncio`. The tests run against `tests/mock_server.py`, a local
HTTP server that behaves like the real service (rate limits, 5xx errors, capped page
sizes). It is test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: job settings (`model`, `job_id`, `batch_size`, `max_concurrency`,
  `max_retries`, `backoff_seconds`, `page_size`). String values are trimmed.
- `data/collections.json`: collections in processing order: `name`, `dimensions`,
  `enabled`.
- `data/documents.csv`: `doc_id`, `collection`, `text`, `updated_at`.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Cleaning

- Collection names and document ids: trim and lower-case. Text: trim.
- `enabled` is a JSON boolean, a number, or a string; as a string `true`, `yes`, `y`
  and `1` (any case) mean enabled. Missing means enabled.
- `updated_at` is `2026-04-03`, `04/03/2026` (month/day/year) or `3 Apr 2026`.
- A document is **skipped** (not sent) when its text is blank or its collection is not
  an enabled collection.

### Batches

1. Collections are processed in `collections.json` order. Within a collection, documents
   are sent oldest `updated_at` first; equal dates keep file order.
2. Each collection's documents are cut into batches of `batch_size` (the last batch may
   be smaller). Batch ids are `<collection>-NN`, numbered from `01` within each collection.
3. Each batch is one `POST {base_url}/v1/embeddings` with headers
   `Authorization: Bearer <api_key>` and `Content-Type: application/json`, and body:

   ```json
   {"model": "<config.model>", "collection": "<name>", "batch_id": "<id>",
    "dimensions": <collection.dimensions>,
    "input": [{"id": "<doc_id>", "text": "<text>"}, ...]}
   ```
4. All batches are started together, but **at most `max_concurrency` requests may be in
   flight at any moment**.

### Retries

- HTTP 429, 500, 502, 503 and 504 are transient. Retry up to `max_retries` times, so a
  batch gets at most `max_retries + 1` attempts. Any other status is final at once.
- Before each retry, wait `Retry-After` seconds if the response has that header (`0` means
  retry straight away), otherwise `backoff_seconds × 2^attempt` (`attempt` starts at 0).
  Waiting goes through the client's async `sleep` function, which tests replace.

### Batch result

- Final status other than 200 → `failed`, with that `http_status`.
- 200 → `ok` if the response has one embedding per input and every embedding has exactly
  the collection's `dimensions`; otherwise `rejected` (http_status 200).

### Commit

After every batch has finished, send exactly one
`POST /v1/jobs/<job_id>/commit` with body
`{"accepted": <sorted ids of ok batches>, "documents": <number of documents in ok batches>}`.

### Index check

For every collection that had at least one batch (in processing order), read the stored
vector ids with `GET /v1/collections/<name>/vectors?offset=<n>&limit=<page_size>`,
starting at offset 0. The response is `{"items": [{"id": ...}], "has_more": bool}`. **The
service may return fewer items than `limit`**; the next offset is the current offset plus
the number of items actually returned. Stop when `has_more` is false or a page is empty.

### Report

`vecsync.reports.build_report(base_url, api_key, sleep=...)` returns:

- `batches`: batch id → `status`, `http_status`, `documents` (doc ids in send order);
- `skipped`: sorted ids of skipped documents;
- `counts`: number of batches per status (`ok`, `failed`, `rejected`);
- `requeue`: sorted doc ids of every `failed` or `rejected` batch;
- `index`: collection → `stored` (number of ids the index lists, including vectors that
  existed before the job) and `missing` (sorted ids from `ok` batches that the index
  does not list).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run the job against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
