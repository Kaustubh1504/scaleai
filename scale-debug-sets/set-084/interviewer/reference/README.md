# Batch Embedding Client

An asyncio client that groups documents into batches, submits each batch as an
embedding job, polls the job until it finishes, pages through the results and reports
the vector norm of every embedded document.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real batch API (rate limits, 5xx errors, slow jobs, failed jobs, paginated results). It
and `tests/helpers.py` are test infrastructure, so leave them alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: client settings (`model`, `batch_size`, `page_size`,
  `max_concurrency`, `max_retries`, `backoff_s`, `poll_interval_s`).
- `data/collections.json`: `name` (trim, lower-case), `enabled` (JSON boolean, number,
  or a string where `true`/`yes`/`y`/`1` mean enabled) and `model` (blank or missing →
  `config.model`).
- `data/documents.csv`: `doc_id` (trim, lower-case), `collection` (trim, lower-case),
  `text` (trim). A document is skipped, checking in this order, as
  `unknown_collection`, `disabled_collection` or `blank_text`.

### Batches

- Within each collection, documents are sorted by id and cut into batches of
  `batch_size`. Batch labels are `<collection>/<n>` with `n` starting at 1; collections
  are processed in alphabetical order.
- At most `max_concurrency` batches are in progress at any moment. A batch is in
  progress from its first create request until its last results page has been read.

### One batch

1. **Create**: `POST /v1/batches` with `{"model", "collection", "inputs": [{"id", "text"}, ...]}`
   and `Authorization: Bearer <api_key>`. Success is `202` with the job `id`.
   - 429 is rate limiting. Wait as long as the server asks (a `Retry-After` header in
     seconds, or `error.retry_after_ms` in the body), then retry.
   - 500, 502, 503 and 504 are transient. Wait `backoff_s × 2^attempt` (`attempt`
     starts at 0) and retry.
   - Both kinds count as retries: at most `max_retries` retries, so at most
     `max_retries + 1` create requests per batch. Other statuses fail the batch at once.
2. **Poll**: `GET /v1/batches/<id>` until `status` is `completed` or `failed`, waiting
   `poll_interval_s` between polls. `failed` fails the batch with reason `error.code`.
3. **Results**: `GET /v1/batches/<id>/results?page_size=<page_size>`, then follow
   `next_page_token` (sent as `&page_token=`) until it is `null`. Every page counts.

Every wait goes through the client's sleep function and is recorded in `waits` as
`[label, "retry" | "poll", seconds]`.

### Report

`embedjobs.reports.build_report(base_url, api_key)` returns:

- `batches`: all batch labels in order;
- `embedded`: doc id → `dims` and `norm` (Euclidean length, rounded to 4 decimals), for
  every document in a batch that succeeded;
- `failures`: label → reason, for **every** batch that did not succeed;
- `skipped`: reason → sorted doc ids;
- `waits`: as above.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py` and `tests/helpers.py`) or
  anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
