# set-020 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What happens inside build_report()?

It loads the config and requests.csv (`load_requests` returns shards and a list of skipped ids), creates a `BatchClient`, runs `asyncio.run(run_all(client, shards))`, then builds per-request rows with `request_rows` and the summary with `summarize`.

### 2. How does run_all start the shards?

It creates `asyncio.Semaphore(client.config.max_concurrency)`, builds one `run_shard(limit, client, shard, items)` coroutine per shard, and awaits `asyncio.gather(..., return_exceptions=True)`. Any exception becomes a `ShardOutcome` with status `error`.

### 3. What does process_shard do, in order?

submit → poll_until_done → (if completed) take `usage.total_tokens` and classify every item from `fetch_results` → archive → return the ShardOutcome.

### 4. What does a results page look like from the mock server?

`{"data": [{"id", "label", "score"}, ...], "page": N, "total_pages": T}`, with `limit` items per page in the order the inputs were submitted. Unknown ids get label `unknown`, score 0.0.

### 5. What does the mock server record that tests can look at?

`requests` (every call with method, path, query, auth header and body), `archived` (batch ids that got a DELETE), and `peak_inflight` (the most submit calls being handled at the same moment; each submit takes about 0.12 s).

### 6. How are retries handled on submit?

`BatchClient.submit` loops `max_retries + 1` times, sleeping `Retry-After` seconds after a 429/5xx response. A final status other than 201 raises `BatchError`.

### 7. Where are skipped requests decided?

In `load_requests`: after trimming, an empty text puts `(shard, id)` on the skipped list and the request is never sent. `request_rows` adds those as `skipped` rows.
