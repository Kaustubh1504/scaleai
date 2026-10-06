# set-060 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside run(), step by step?

It loads the config, builds an EmbeddingClient, calls fetch_all to page through the dataset, select() to filter and clean records, make_batches to cut them into b1..bN, gathers embed_batch for every batch, then calls commit() for the ok batches (catching UpsertError) and assembles the report.

### 2. How does transport.request work with asyncio?

It runs the blocking urllib call `_send` via asyncio.to_thread. `_send` returns a Response for 2xx and also for HTTPError (4xx/5xx), with the status, headers and JSON-decoded body; it never raises for an HTTP status.

### 3. How does fetch_all move from page to page?

It calls client.records_page(token), starting with None; records_page adds `page_token` to the query when a token is given. fetch_all counts pages, reads `next_page_token` from each page and stops when it is falsy.

### 4. What does with_retries return, and what counts as retryable?

(response, attempts). It loops calling call(), returning when the status is not in RETRYABLE {429, 500, 502, 503, 504} or attempt > max_retries; otherwise it calls asyncio.sleep with backoff_delay(response, attempt, base).

### 5. What can parse_embeddings raise?

ResponseError if the body has no data list or the indexes aren't exactly 0..count-1, and DimensionMismatch (a subclass of ResponseError) if any vector's length differs from the configured dimensions. It returns vectors sorted by index.

### 6. Where is the semaphore used?

EmbeddingClient.__init__ creates `self.sem = asyncio.Semaphore(config.max_concurrency)`. `upsert` acquires it around its request; look at embed_batch to see how it sends the embeddings request.

### 7. What does the mock server do with each batch?

b2 gets two 503s then succeeds, b3 a 429 with Retry-After: 0 then succeeds, b4 succeeds but with 3-dim vectors, b5 always gets 400, b1's data comes back in reverse index order, and the index upsert for b6 returns 500. Each embeddings request sleeps 50 ms and the server tracks the maximum number in flight.
