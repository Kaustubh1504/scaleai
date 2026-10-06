# set-044 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside run()?

It loads the config and corpus, builds batches with `make_batches`, creates an `EmbeddingClient`, awaits `embed_all(batches)`, then awaits `list_index_ids` and builds the report dicts from the vectors, the failures, `client.usage_tokens` and the index ids.

### 2. How does the transport make HTTP calls without blocking the event loop?

`transport.request` runs the blocking urllib call in `asyncio.to_thread`. HTTP errors come back as a `Response` with the error status rather than an exception.

### 3. How are response embeddings matched to doc ids?

Each `data` item has an `index`; `_embed_batch` maps `batch.doc_ids[item["index"]]` to `item["embedding"]`. The mock server returns the items in reverse order.

### 4. What does the mock server do for each batch?

Every embeddings call sleeps 50 ms and tracks in-flight requests (`max_in_flight`). b2 gets a 429 with `Retry-After: 0.2` and then succeeds, b4 always returns 503, b6 returns 400, and the rest return 200 with word-count tokens. It also records each request's arrival time in `at`.

### 5. Where is concurrency controlled?

`EmbeddingClient.__init__` creates `self._sem` from `max_concurrency`. `_run_batch` wraps `_embed_batch` in an `async with` block on a semaphore, and `embed_all` starts every batch with `asyncio.gather`.

### 6. How does list_index_ids know when to stop?

It loops: request a page with `limit` (and `cursor` when it has one), then read `next_cursor` from the body, and break when it is falsy. The ids are collected with `ids.extend(...)` inside the same loop.

### 7. How is a batch's failure represented?

`_embed_batch` raises `BatchFailed("HTTP <status>")` when the final response isn't 200. `embed_all` uses `gather(..., return_exceptions=True)`, so the exception comes back as that batch's result.
