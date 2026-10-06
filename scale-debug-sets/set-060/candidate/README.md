# Embedding Backfill

An async client that reads every record of a support-FAQ dataset from a paginated API,
picks the records that need embedding, sends them to an embeddings endpoint in
concurrent batches (with retries), and finally commits the good vectors to a vector
index.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real API (pagination, rate limits, 5xx errors, a flaky index). It is test
infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Configuration

`data/config.json`: `dataset`, `model`, `dimensions`, `since`, `page_size`,
`batch_size`, `max_concurrency`, `max_retries`, `backoff_s`. All requests send
`Authorization: Bearer <api_key>`.

### 1. Read the dataset

- `GET {base}/v1/datasets/<dataset>/records?limit=<page_size>`, then repeat with
  `&page_token=<next_page_token>` until `next_page_token` is `null`. Every page's
  records are part of the dataset, including the last page.
- `fetched` = number of records read; `pages` = number of pages requested.

### 2. Select records

A record is embedded unless its `status` is `deleted` (any case), its `text` is blank
after trimming, or its `updated` date is before `since`. `updated` is `2026-03-02`,
`03/02/2026` (month/day/year) or `2026-03-02T09:00:00Z`. Ids are trimmed and
lower-cased; texts are trimmed. Selected records keep dataset order.

### 3. Embed

- Selected records are split, in order, into batches of `batch_size`: `b1`, `b2`, ...
- Each batch is one `POST {base}/v1/embeddings` with body
  `{"model", "input": [texts], "dimensions", "metadata": {"batch_id"}}`.
- At most `max_concurrency` embedding requests may be in flight at any moment.
- HTTP 429/500/502/503/504 are retried up to `max_retries` times (at most
  `max_retries + 1` attempts). After failed attempt *n* (the first attempt is 1), wait
  `Retry-After` seconds if the header is present, otherwise `backoff_s × 2^(n−1)`.
- Batch result `status`:
  - final HTTP status ≥ 400 → `http_error` (the body is not parsed);
  - otherwise the body is parsed: `data[i].index` says which input a vector belongs to
    (the server may return them in any order). If any vector's length differs from
    `dimensions` → `dim_mismatch`; any other unusable body → `bad_response`;
  - otherwise `ok`.
- Each batch reports `status`, `http_status` (final), `attempts` and `records` (ids).

### 4. Commit

Every `ok` batch is sent to `POST {base}/v1/index/upsert` (concurrently, same
concurrency limit, no retries). A non-200 response means that batch failed to commit.
One batch failing must not affect the others: `commit` lists `committed` and `failed`
batch ids (sorted).

### Report

`vecsync.runner.build_report(base_url, api_key)` returns `fetched`, `pages`, `selected`
(ids), `batches`, `vectors` (record id → vector, for `ok` batches), `total_tokens`
(sum of `usage.total_tokens` over `ok` batches) and `commit`.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run the backfill against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
