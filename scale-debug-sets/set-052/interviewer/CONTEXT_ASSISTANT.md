# set-052 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do end to end?

It loads config.json and documents.csv, then runs `run_index` with asyncio.run. run_index builds batches with `make_batches`, starts `client.embed_batch` for all of them under one asyncio.gather, then calls `fetch_usage`. build_report turns the BatchResults into `batches`, `vectors` and `summary`.

### 2. How does send_with_retries count attempts?

It loops: sends a request, returns `(response, attempt + 1)` if the status isn't in RETRYABLE or attempt has reached max_retries, otherwise sleeps for `wait_time(...)` via the injected sleep and increments attempt.

### 3. Where does the client limit concurrency?

`EmbeddingClient.__init__` creates `self.limit = asyncio.Semaphore(config.max_concurrency)`. The HTTP call in embed_batch is wrapped in an `async with` block around send_with_retries.

### 4. How are options per collection built?

In embed_batch, `options` starts from the client's `defaults` (copied from config.defaults in __init__) and is updated with `config.options_for(batch.collection)`. `options.get('normalize')` is checked when each vector is processed, after the response arrives.

### 5. What does parse_vectors return for an error body?

It reads `body['data']` when the body is a dict, defaulting to an empty list, sorts the items by `index` and returns their embeddings. For an error body without `data` it returns [].

### 6. How does the mock server paginate usage?

GET /v1/usage returns `{"data": rows, "next_cursor": ...}` where rows are `limit` records from an offset encoded in the cursor; next_cursor is null when there are no more. One usage record is added per 200 embeddings response, in completion order.

### 7. What does tally compute?

For the results passed in, it adds `len(r.doc_ids)` to `docs` and `len(r.vectors)` to `embedded` in a counts dict and returns it. summarize calls it once per collection with that collection's results.
