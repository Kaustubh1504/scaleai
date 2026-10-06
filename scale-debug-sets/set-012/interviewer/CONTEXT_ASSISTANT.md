# set-012 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() do end to end?

It calls `asyncio.run(pipeline.run(...))`, which loads the config and documents, splits them into batches with `make_batches`, embeds every batch through `asyncio.gather` over `client.embed_batch`, and then calls `collect_usage`. build_report then maps each document to its batch status, collects vectors of embedded documents, sums usage tokens and calls `near_duplicates`.

### 2. How does transport.request make an HTTP call without blocking the event loop?

It runs the synchronous `_send` (urllib) in a worker thread via `asyncio.to_thread`. `_send` returns a `Response(status, headers, text)` for both 2xx and HTTP error statuses; network errors raise.

### 3. Where is the concurrency limit configured and created?

`max_concurrency` comes from config.json (2 in the data). `EmbeddingClient.__init__` creates `self.semaphore = asyncio.Semaphore(config.max_concurrency)`; `_post` is the method that sends each attempt's POST.

### 4. What does send_with_retries return, and how is the delay chosen?

It returns a tuple `(response, attempts)`. `retry_delay` uses the `Retry-After` header as seconds when present, otherwise `backoff_seconds * 2 ** attempt` with the zero-based attempt passed in.

### 5. What can parse_embeddings raise?

`json.loads` raises `json.JSONDecodeError` when the body is not JSON. It raises `ValueError` itself when `data` is missing, has the wrong number of items, a vector has the wrong length, or the indexes don't cover 0..n-1.

### 6. What does the mock server return from /v1/usage?

Records whose id is greater than the `after` query value (string comparison on ids like u001), at most `limit` of them, plus `first_id` and `last_id` of the returned rows and `has_more`, which is true when more records remain beyond this page.

### 7. How does the mock server script each batch?

`SCRIPT` maps batch id to a list of responses served in order, the last one repeating. b02 gets a 429 with Retry-After 0.3 then succeeds, b03 a 500 then success, b04 is always 503, b05 returns a cut-off JSON body, b07 returns one embedding too few, and the rest succeed. Every 200 adds a usage record.
