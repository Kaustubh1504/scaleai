# Embedding Indexer

An async client that turns help-centre documents into embeddings. It batches the
documents per collection, sends the batches to an embeddings endpoint with a cap on how
many requests are in flight, retries transient failures, post-processes the vectors, and
finally reads the paginated usage records to report how many tokens the run cost.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real endpoint (rate limits, 5xx errors, validation errors, unordered results, paginated
usage). It is test infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: run settings. Keys that are present are used exactly as given;
  defaults apply only to missing keys. Collection names in `collections` are trimmed and
  lower-cased.
- `data/documents.csv`: `doc_id` and `collection` are trimmed and lower-cased. `text` is
  trimmed and runs of whitespace are collapsed to one space; rows whose text is then
  empty are skipped. `updated` is `2026-04-02`, `04/02/2026` (month/day/year) or
  `2 Apr 2026`.
- A `doc_id` can appear more than once. Only the row with the latest `updated` counts,
  but the document keeps the position where its id first appeared.

### Batches

- Group documents by collection, collections in alphabetical order. Inside a collection
  keep document order and cut it into batches of `batch_size`.
- Batch ids are `<collection>-NN`, numbered from `01` within each collection.
- All batches are started together, but **at most `max_concurrency` requests may be in
  flight at any moment** across the whole run.

### Request

`POST {base_url}/v1/embeddings` with `Authorization: Bearer <api_key>` and body:

```json
{"model": "<config.model>", "input": ["<text>", ...], "dimensions": <config.dimensions>, "user": "<batch id>"}
```

### Retries

- HTTP 429, 500, 502, 503 and 504 are transient. Retry them up to `max_retries` times
  (at most `max_retries + 1` attempts in total).
- Before each retry, wait `Retry-After` seconds if the response has that header,
  otherwise `backoff_seconds × 2^n`, where `n` is the number of retries already made
  (so 0 for the first). The wait must actually happen through the client's `sleep`.
- Any other status is final straight away.

### Results

- A batch whose final status is anything other than 200 is `failed`, with that
  `http_status` and no vectors.
- Otherwise it is `ok`. The response's `data` items carry an `index` that points back
  into `input`; the order of `data` itself means nothing.
- Each collection's options are `config.defaults` overlaid with
  `config.collections[<collection>]`. If `normalize` is true, the vector is scaled to
  unit length (L2). Every value is then rounded to 4 decimals.

### Usage and summary

- After every batch has finished, read the usage records with
  `GET /v1/usage?limit=<usage_page_size>` and follow `next_cursor` (sent as `&cursor=`)
  until it is `null`. Every page counts, the first one included.
- `summary`:
  - `docs`: documents sent in a batch (counting failed batches); `embedded`: documents
    that got a vector;
  - `by_collection`: collection → `{"docs", "embedded"}` for that collection alone;
  - `total_tokens`: sum of `total_tokens` over all usage records.

`embedindex.reports.build_report(base_url, api_key, sleep=...)` returns `batches`
(batch id → `docs`, `status`, `http_status`, `attempts`), `vectors` (doc id → vector)
and `summary`.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run the indexer against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
