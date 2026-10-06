# Embedding Indexer

An asyncio client that embeds a small help-centre corpus through an embeddings endpoint,
stores every vector in a vector index, and reports token usage and near-duplicate
documents. Batches are sent concurrently, but never more than the configured number of
requests may be in flight at once.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real API (rate limits, 5xx errors, out-of-order embedding lists, an index that can refuse
a vector). It is test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: `model`, `batch_size`, `max_concurrency`, `max_retries`,
  `backoff_seconds`, `similarity_threshold`. Defaults apply only to missing keys.
- `data/documents.csv`: `doc_id` (trim, lower-case), `text` (trim), `updated`
  (`2026-02-01`, `02/01/2026` month/day/year, or `Feb 1 2026`).
  - Rows with blank text are ignored.
  - If a `doc_id` appears more than once, keep the row with the latest `updated`. On the
    same date, the later row in the file wins.
  - Documents are processed in `doc_id` order.

### Embedding

- Split the documents into consecutive batches of `batch_size`; batch `i` (from 0) is
  `POST {base_url}/v1/embeddings` with headers `Authorization: Bearer <api_key>` and
  `Content-Type: application/json` and body
  `{"model": ..., "input": [<texts>], "metadata": {"batch": i}}`.
- All batches are started together, but at most `max_concurrency` HTTP requests (to any
  endpoint) may be in flight at any moment.
- A 200 response has `data: [{"index": k, "embedding": [...]}, ...]` (in any order;
  `index` is the position in `input`) and `usage.prompt_tokens`.
- HTTP 429, 500, 502, 503 and 504 are transient: retry up to `max_retries` times, so at most
  `max_retries + 1` attempts per batch. Before each retry, wait `Retry-After` seconds if
  the header is present, otherwise `backoff_seconds × 2^attempt` (`attempt` starts at 0).
  Do not wait after the final attempt.
- A batch whose final status is ≥ 400 fails: it is listed in `failed_batches` as
  `{"batch": i, "status": <status>, "doc_ids": [...]}` and its documents get no vector.

### Indexing

- Every embedded document is stored with `PUT {base_url}/v1/index/<doc_id>` and body
  `{"model": ..., "embedding": [...]}`. A 200 returns `{"version": n}`.
- Any other status means the index refused that document. Refusals do not stop the run;
  they are listed (sorted) in `index.rejected`, and `index.stored` counts the successes.

### Report

`vecsync.reports.build_report(base_url, api_key)` returns:

- `embedded`: sorted ids of documents that received a vector;
- `failed_batches`: as above, in batch order;
- `index`: `{"stored": <count>, "rejected": [<doc_id>, ...]}`;
- `summary`:
  - `documents`: documents loaded (after cleaning and de-duplication);
  - `embedded`: documents with a vector;
  - `total_tokens`: sum of `prompt_tokens` over successful batches;
  - `tokens_per_doc`: `total_tokens ÷ embedded`, rounded to 2 decimals;
  - `near_duplicates`: every pair of embedded documents whose cosine similarity is
    **at least** `similarity_threshold`, as `[doc_a, doc_b, similarity]` with
    `doc_a < doc_b`, sorted. The comparison uses the exact similarity; only the reported
    value is rounded (3 decimals).

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run the pipeline against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py` and `tests/helpers.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
