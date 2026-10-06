# set-068 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside build_report()?

It runs run_backfill with asyncio.run: load_config, load_documents, make_batches, then EmbeddingClient.embed_all, which gathers embed_batch for every batch. The outcomes are turned into the batches and docs dicts, and summarize builds the summary.

### 2. How does a request reach the server?

embed_batch encodes the body with payloads.encode_body (json.dumps with a default hook for datetimes), then calls send_with_retries with a lambda that awaits transport.post. post runs the blocking send_sync in a worker thread via asyncio.to_thread.

### 3. What does send_with_retries return?

A tuple (last Response, number of attempts). It stops at the first status outside TRANSIENT, or when the attempt counter reaches max_retries, and sleeps for retry_delay(...) between attempts.

### 4. What does the mock server do for each batch id?

SCRIPT in tests/mock_server.py: b01/b07 succeed, b02 gets 429 with Retry-After 0.3 and then 200, b03 succeeds with its data items reversed, b04 always returns 503, b05 returns 400, b06 returns 500 and then 200. Every request takes about 0.08 s and the server tracks max_in_flight.

### 5. Where is the concurrency limit set up?

EmbeddingClient.__init__ creates self._limit = asyncio.Semaphore(config.max_concurrency); config.json sets max_concurrency to 2. embed_batch acquires a semaphore around the call to send_with_retries.

### 6. How is a document's norm computed?

client.vector_norm takes the square root of the sum of squared components and rounds to 3 decimals. build_report applies it to the vector stored for each doc id in the outcome's `vectors` dict.

### 7. Where does tokens_per_doc come from?

summarize adds up outcome['tokens'] (usage.total_tokens for ok batches, 0 for failed ones) and divides by the number of embedded documents, rounded to 2 decimals.
