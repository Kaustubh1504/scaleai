# set-092 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What is the overall flow of build_report()?

It loads the config, documents and retired ids, then runs `sync.run_sync` with `asyncio.run`. run_sync lists the index for each collection, marks unchanged documents as skipped, collects index ids that are not active into to_delete, batches the rest with `documents.make_batches`, and calls `client.embed_all`. It then walks the batch outcomes to fill outcomes, embeddings, errors and total_tokens. `reports.summarize` builds the summary.

### 2. How does the HTTP layer work with asyncio here?

`transport.send` encodes the payload with `encode_body` and runs the blocking `_send_sync` (urllib) in a worker thread via `asyncio.to_thread`. `_send_sync` returns a `Response(status, headers, body)` for both 2xx and HTTP error statuses.

### 3. What does embed_all return, and in what order?

It creates `self._limit` and returns the result of `asyncio.gather` over `_bounded(batch)` for each batch. Plain gather results come back in the same order as the batches passed in; with `return_exceptions=True` a raised exception appears as a value in that list.

### 4. What does the mock server do differently for some batches?

SCRIPT in mock_server.py: faq-1 gets one 429 with `Retry-After: 0.25`, policies-0 gets one 500, and products-1 gets 503 on every attempt. Every embedding request is held for 40 ms, and the server tracks the largest number in flight in `max_in_flight`.

### 5. How does the mock index paginate?

GET /v1/index/<collection> returns `limit` items from an offset plus `next_page_token`, an opaque base64 token, or null when there are no more items. faq and products have empty indexes. policies has 10 entries, so with page_size 4 it takes three pages.

### 6. How does the test harness record backoff?

`tests/harness.SyncRun.sleep` is an async function that appends the requested seconds to `self.delays` and returns at once. build_report passes it through to `EmbeddingClient`, which gives it to `with_retries`.

### 7. How does embed_batch map vectors back to documents?

For each item in the response's `data`, it uses `item["index"]` as a position in `batch.docs` and stores `item["embedding"]` under that document's id. It returns `(vectors, usage.total_tokens)`, or raises `BatchError` if the final status is not 200.
