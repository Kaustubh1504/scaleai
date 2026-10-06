# set-036 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, end to end?

It loads config.json and documents.csv, builds an EmbeddingClient, and runs run_pipeline inside asyncio.run. run_pipeline embeds all batches concurrently with asyncio.gather, then upserts every returned vector with another gather. The report has the embedded doc ids, failed batches, index results and a summary.

### 2. How are documents batched and numbered?

load_documents returns the latest version of each doc_id (blank text skipped), sorted by id. batched() slices that list into chunks of batch_size (4). The chunk's position becomes metadata.batch in the request body, which the mock server uses to pick its scripted response.

### 3. What does the mock server send for each batch?

Batch 0 and 3: 200. Batch 1: 429 with Retry-After 2, then 200. Batch 2: 503 every time. Batch 4: 500, then 200. Successful responses list the embeddings in reverse order, each with its input index, plus usage.prompt_tokens (number of words).

### 4. How does the test harness observe concurrency and waits?

The mock server counts requests in flight (each embeddings call takes 40 ms) and keeps the maximum in peak_in_flight. tests/helpers.py passes a Waits object as the client's sleep: an async callable that appends each requested delay and returns immediately.

### 5. Where is the concurrency limit created?

EmbeddingClient.__init__ creates self.limit = asyncio.Semaphore(config.max_concurrency). embed_batch and upsert each wrap their HTTP work in an `async with` block.

### 6. What happens when the index refuses a vector?

The server returns 409 for d07. client.upsert raises UpsertError for any non-200. index_vectors gathers all upserts with return_exceptions=True and sorts each result into run.rejected or run.stored.

### 7. How is a near duplicate decided?

similarity.near_duplicates compares every pair of embedded documents (sorted ids) with cosine similarity and keeps pairs at or above similarity_threshold (0.95), appending [doc_a, doc_b, similarity rounded to 3 decimals].
