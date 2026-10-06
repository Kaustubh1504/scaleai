# Embedding Sync

An asyncio job that sends help-centre articles to an embeddings endpoint in small
batches, a few at a time, retries transient failures, and then reads the per-request
usage records (paginated) to report token spend and near-duplicate articles.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real endpoint (rate limits, 5xx errors, slow responses, malformed bodies, paginated
usage). It is test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: client settings. Keys missing from the file fall back to the
  defaults in `vecbatch/config.py`.
- `data/documents.csv`: `doc_id` (trim, lower-case), `status`, `updated`, `text`.
  Rows whose `status` is `archived` (any case) or whose `text` is blank are not sent.
  Text is trimmed before sending. `updated` is informational only.

### Batching and concurrency

- Documents are sent in file order, `batch_size` per batch. Batches are numbered
  `b01`, `b02`, … in that order; the last batch may be smaller.
- Batches run concurrently, but **at most `max_concurrency` requests may be in flight
  at once**. Waiting between retries does not count as in flight.

### Request

`POST {base_url}/v1/embeddings` with headers `Authorization: Bearer <api_key>` and
`Content-Type: application/json`, and body:

```json
{"model": "<config.model>", "input": ["<text>", "..."], "dimensions": <config.dimensions>,
 "metadata": {"batch_id": "<batch id>"}}
```

### Retries

- HTTP 429, 500, 502, 503 and 504 are transient. Retry them up to `max_retries` times,
  so there are at most `max_retries + 1` attempts per batch.
- Before the next attempt, wait `Retry-After` seconds if the response has that header,
  otherwise `backoff_seconds × 2^n` where `n` is 0 after the first attempt, 1 after the
  second, and so on. The job must really wait; it may not send early.
- Any other status is final straight away.

### Batch result (applies to every document in the batch)

- Final status ≥ 400 → `http_error`.
- Status 200 whose body is not valid JSON → `bad_json`.
- Status 200 with JSON that does not contain exactly one embedding of length
  `dimensions` per input (matched by `index`) → `invalid`.
- Otherwise → `embedded`, and each document gets the vector with its index.

### Usage

- After all batches finish, read the usage records with
  `GET /v1/usage?limit=<usage_page_size>`. Each page has `data`, `first_id`, `last_id`
  and `has_more`. While `has_more` is true, request the next page with
  `&after=<last_id of the page just read>`. Each record must be counted exactly once.

### Report

`vecbatch.reports.build_report(base_url, api_key)` returns:

- `batches`: batch id → `status`, `attempts`;
- `documents`: doc id → status of its batch;
- `counts`: `embedded` = number of embedded documents, `failed` = all others;
- `total_tokens`: sum of `total_tokens` over all usage records;
- `near_duplicates`: every pair of embedded documents whose cosine similarity, rounded to
  3 decimals, is **at least** `duplicate_threshold`, as `[doc_a, doc_b, similarity]`
  with `doc_a < doc_b`. Most similar pair first; equal similarity sorted by `doc_a`, then
  `doc_b`.

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
