# Embedding Backfill

An asyncio client that backfills vector embeddings for help-centre documents. It splits
the documents into fixed-size batches, sends the batches to an embeddings endpoint with
a cap on how many requests are in flight, retries transient failures, and reports the
vector norm of each embedded document plus a run summary.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real endpoint (rate limits, 5xx errors, simulated model latency, and response items
that are not always in input order). It is test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: `model`, `batch_size`, `max_concurrency`, `max_retries`,
  `backoff_s`, `timeout_s`. Defaults apply only to keys that are missing.
- `data/documents.csv`: `doc_id` (trim, lower-case), `collection` (trim, lower-case),
  `text` (trim), `updated_at` (`2026-04-01 09:00`, `04/01/2026 09:00` month/day/year, or
  `2026-04-01T09:00:00`). Rows whose text is blank are skipped.

### Batches and requests

- Documents are cut into batches of `batch_size` in file order (after skipping blanks).
  Batch ids are `b01`, `b02`, ... in that order.
- Each batch is one `POST {base_url}/v1/embeddings` with headers
  `Authorization: Bearer <api_key>` and `Content-Type: application/json`, and body:

```json
{
  "model": "<config.model>",
  "input": ["<text>", "..."],
  "metadata": {
    "batch_id": "b01",
    "doc_ids": ["<doc_id>", "..."],
    "newest_update": "<latest updated_at in the batch, ISO 8601: 2026-04-03T08:15:00>"
  }
}
```

- All batches are started together, but **at most `max_concurrency` requests may be in
  flight** at any moment, across all batches (retries included).

### Retries

- HTTP 429, 500, 502, 503 and 504 are transient. Retry them up to `max_retries` times,
  so a batch gets at most `max_retries + 1` attempts in total.
- Before the next attempt, wait `Retry-After` seconds if the response has that header
  (it may be fractional), otherwise `backoff_s × 2^attempt` (`attempt` starts at 0).
  The wait must really happen before the next request is sent.
- Any other status is final straight away.

### Results

- A batch whose final status is 200 is `ok`. Each item in the response's `data` list has
  an `index` (position in the request's `input`) and an `embedding`. **Items may arrive
  in any order**; use `index` to match them to documents. `usage.total_tokens` is the
  batch's token count.
- Any other final status makes the batch `failed`; its documents are failed with that
  `http_status` and it contributes 0 tokens.
- A document's `norm` is the Euclidean length of its embedding, rounded to 3 decimals.

### Report

`embedclient.reports.build_report(base_url, api_key)` returns:

- `batches`: batch id → `doc_ids`, `status`, `http_status`, `attempts`;
- `docs`: doc id → `{"status": "ok", "norm": ...}` or `{"status": "failed", "http_status": ...}`;
- `summary`: `embedded` and `failed` document counts, `total_tokens`, `tokens_per_doc`
  (total tokens ÷ embedded documents, rounded to 2 decimals) and `by_collection`
  (collection → embedded documents).

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
