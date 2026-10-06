# Guideline Embedder

Labeling guidelines are stored as short rule snippets. This async client sends every
snippet to an embeddings endpoint in batches, a few batches at a time, retries transient
failures, and then lists the remote vector index to find entries that no longer exist in
the corpus. It prints a summary of the run.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real endpoint (latency, rate limits, 5xx errors, cursor-paginated index listing). It is
test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: client settings. Defaults apply only to keys that are missing.
- `data/corpus.csv`: `doc_id` (trim, lower-case), `title`, `text` (trim). Rows with a
  blank text are skipped. If an id appears more than once, only its first row is used.

### Batching and requests

- Docs are split, in file order, into batches of `batch_size`. Batches are named `b1`,
  `b2`, … in order.
- Each batch is one `POST {base_url}/v1/embeddings` with headers
  `Authorization: Bearer <api_key>` and `Content-Type: application/json`, and body
  `{"model": <config.model>, "input": [<texts>], "metadata": {"batch": "<batch id>"}}`.
- All batches are started together, but **at most `max_concurrency` requests may be in
  flight at any moment**.
- The response's `data` items carry an `index` into the batch's `input` list. They are
  not guaranteed to come back in order. `usage.total_tokens` is the batch's token count.

### Retries

- HTTP 429, 500, 502, 503 and 504 are transient. Retry them up to `max_retries` times,
  so there are at most `max_retries + 1` attempts per batch.
- Before a retry, wait `Retry-After` seconds if the response has that header (it may be
  fractional), otherwise `backoff_seconds × 2^attempt` (`attempt` starts at 0). The wait
  must actually happen before the next attempt is sent.
- Any other status is final straight away. A batch whose final status isn't 200 has
  **failed**: it contributes no vectors and no tokens, and it must be listed in `failed`
  as `"HTTP <status>"`. A failed batch must not stop the other batches.

### Index listing

After embedding, read every id in the remote index with
`GET /v1/index?limit=<index_page_size>`, then follow `next_cursor` (sent as `&cursor=`)
until it is `null`. **Every** page's ids count, including the last page's.

### Report

`embedclient.report.build_report(base_url, api_key)` returns:

- `batches`: batch id → doc ids;
- `vectors`: doc id → embedding, for docs in successful batches;
- `failed`: batch id → `"HTTP <status>"` for every failed batch;
- `summary`:
  - `embedded`: number of docs with a vector;
  - `missing_docs`: sorted ids of corpus docs without a vector;
  - `total_tokens`: sum of `usage.total_tokens` over all successful batches;
  - `stale_ids`: sorted ids that are in the remote index but not in the corpus.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
