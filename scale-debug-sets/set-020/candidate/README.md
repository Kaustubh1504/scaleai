# Batch Labeling Client

An async client for a batch image-tagging API. Requests are grouped into shards; each
shard is submitted as one batch job, polled until the job finishes, and its results are
downloaded page by page. Low-confidence labels are routed to human review, and the run
ends with a short cost summary.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real API (rate limits, slow job completion, a failing job, paginated results). It is test
infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: client settings (see below).
- `data/requests.csv`: `request_id`, `shard`, `text`. Request ids and shard ids: trim and
  upper-case (` r17` → `R17`, `s2 ` → `S2`). Text is trimmed; a request whose text is
  blank (or only spaces) is **not sent** and is reported as `skipped`.
- Each shard's requests are sent in file order.

### Per shard

1. **Submit**: `POST {base_url}/v1/batches` with header `Authorization: Bearer <api_key>`
   and body `{"model": <config.model>, "shard": "<shard>", "inputs": [{"id": ..., "text": ...}, ...]}`.
   A `201` returns `{"id": "<batch_id>", "status": "queued"}`. HTTP 429/5xx are
   retried up to `max_retries` times (wait `Retry-After` seconds). Any other non-201
   status, or running out of retries, makes the shard `error`.
2. **Poll**: `GET /v1/batches/<batch_id>` up to `max_polls` times, `poll_interval_s`
   apart, until `status` is `completed` or `failed`. If it never gets there, the shard is
   `timeout`. A completed batch reports `usage.total_tokens`.
3. **Results** (completed batches only): `GET /v1/batches/<batch_id>/results?page=N&limit=<page_size>`,
   starting at `page=1`. Each response has `data`, `page` and `total_pages`. **Every**
   page from 1 to `total_pages` must be read.
4. **Archive**: after a batch has finished (completed or failed) and its results are
   read, `DELETE /v1/batches/<batch_id>`. Every submitted batch must be archived.
5. At most `max_concurrency` shards may be in progress at once (from submit to archive).
   One shard failing must not stop the others.

### Per request

- In a completed shard: a result with `score >= review_threshold` is `labeled`; a lower
  score is `needs_review` (both keep `label` and `score`). A request with no result row
  is `missing`.
- In a shard that did not complete: the request gets the shard's status (`failed`,
  `timeout` or `error`) with `label` and `score` set to `None`.

### Report

`labelbatch.reports.build_report(base_url, api_key)` returns:

- `requests`: request id → `shard`, `status`, `label`, `score`.
- `summary`:
  - `shards`: shard id → final shard status;
  - `total_tokens`: sum of `usage.total_tokens` over completed batches;
  - `cost_usd`: `total_tokens × price_per_1k_tokens ÷ 1000`, rounded to 4 decimals.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run the batch against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
