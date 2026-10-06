# set-084 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside build_report?

It loads config, collections and documents, builds the batches with `make_batches`, creates a `BatchClient`, runs `runner.run_batches` with `asyncio.run`, then turns the embeddings into dims/norm and returns batches, embedded, failures, skipped and the client's `waits` list.

### 2. What does run_one do for a single batch?

Inside an `async with` block it calls `create_with_retries`, then `client.wait_until_done`, then `client.results`, and returns a dict of doc id → embedding vector.

### 3. How are errors classified from an HTTP response?

`errors.raise_for_status` raises `RateLimited` (with `retry_after_seconds`) for 429, `TransientError` for 500/502/503/504, and `ApiError` for any other status >= 400. RateLimited is a subclass of TransientError, which is a subclass of ApiError.

### 4. How does the mock server behave for each collection?

legal's first create returns 429 with `retry_after_ms: 120`; product's first two creates return 500 and 503; news jobs need 4 polls before completing; any job with an input over 120 characters finishes as `failed` with code `input_too_long`. Results pages include `page_token` (the token sent) and `next_page_token`.

### 5. What does BatchClient.pause record?

It appends `[label, kind, round(seconds, 3)]` to `self.waits` and then awaits the injected `sleep` function. Tests inject a sleep that returns immediately.

### 6. Where does the number of create attempts come from?

`create_with_retries` loops `range(client.config.max_attempts)`; `max_attempts` is a property on `Config` in config.py. It pauses between attempts but not after the last one, then raises `ApiError('retries_exhausted')`.

### 7. How does the server measure concurrency?

Every request increments an in-flight counter on arrival and decrements it after replying (each request takes about 20 ms). `max_inflight` is the peak value.
