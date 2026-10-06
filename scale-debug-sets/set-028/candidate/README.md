# Embedding Backfill

A batch job that embeds a help-desk document set with two embedding models, one after
the other, through an async HTTP client. Identical texts are embedded once per model,
and vectors are cached so a text is never sent twice to the same model. Afterwards the
job reads the provider's usage ledger (paginated) to report billed tokens.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real provider (rate limits, overload errors, input limits, out-of-order results,
paginated usage). It is test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: `models` (comma-separated; run in the listed order; trim each name),
  `batch_size`, `max_concurrency`, `max_retries`, `backoff_seconds`, `page_size`.
- `data/documents.csv`: `doc_id` (trim, lower-case) and `text`. Text is normalised by
  trimming and collapsing runs of whitespace to one space. Rows whose text is blank
  after that are skipped.

### Embedding (per model)

1. Take the distinct normalised texts in first-seen order, leaving out any text that
   is already cached **for that model**. Split them into batches of `batch_size`.
2. Send every batch as `POST {base_url}/v1/embeddings` with
   `{"model": <model>, "input": [<texts>]}` and the headers
   `Authorization: Bearer <api_key>`, `Content-Type: application/json`.
   Batches run concurrently, but **never more than `max_concurrency` requests may be
   in flight at once** (retries included).
3. HTTP 429, 500, 502, 503 and 504 are transient. Retry them up to `max_retries` times
   (at most `max_retries + 1` attempts). Before each retry, wait `Retry-After` seconds
   if the response has that header, otherwise `backoff_seconds × 2^attempt` (attempt
   starts at 0). The wait must actually happen; the client's `sleep` is an async
   function.
4. Any final status other than 200 fails the whole batch: `http_status` is that status
   and `reason` is `transient` for the statuses in rule 3, `rejected` for anything else.
5. A 200 response holds `data`: one `{"index", "embedding"}` per input, **in any
   order**; match them up by `index`. If the count doesn't match the inputs, the batch
   fails with `http_status` `null` and `reason` `invalid_response`.
6. Successful vectors are cached under (model, text).

### Usage

- After all models are done, read `GET /v1/usage?limit=<page_size>` and follow
  `next_cursor` (passed back as `&cursor=`) until it is `null`. The server may return
  **fewer** records than `limit` on any page, so a short page is not the end.
- Every 200 embedding response produces one usage record (`model`, `tokens`).

### Report

`embedq.reports.build_report(base_url, api_key, sleep=None)` returns:

- `documents`: per doc id, per model, either `{"status": "ok", "dims": <vector length>}`
  or `{"status": "failed", "http_status": ..., "reason": ...}`.
- `summary`: per model, `ok` and `failed` document counts and `billed_tokens` (sum of
  that model's usage records).

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
