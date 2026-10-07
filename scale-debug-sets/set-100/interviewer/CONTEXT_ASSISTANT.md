# set-100 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, step by step?

It loads config, suites and prompts (sorted by priority then id), creates a RelayClient and a Runner, awaits `runner.run_all(prompts)` to get completions and failures, fetches baselines with `fetch_baselines` and reduces them with `latest_baselines`, then builds the report dict (answers, finish reasons, tokens, passed, blocked, failed, attempts, suites, regressions, new prompts).

### 2. How does wire.send talk to the server?

It opens a connection with `asyncio.open_connection`, writes one HTTP/1.1 request built by `_encode_request` from the headers dict it was given, reads the status line and headers, then reads the body either chunked (`_read_chunked`), by Content-Length, or to EOF. It returns a `Response(status, headers, body)` with lower-cased header names and closes the connection.

### 3. Where does the concurrency limit live?

Runner creates `self.limit = asyncio.Semaphore(config.max_concurrency)` once. `run_one` holds it around the `with_retries` call (all attempts and backoff waits for one prompt). The policy check happens before the semaphore is acquired.

### 4. What does the mock relay do for the special prompts?

p03 gets 429 with `Retry-After: 1.5`, then 503, then a stream; p07 always gets 400; p11 always gets 503; p10's stream has no done event; p02's deltas arrive in the order 3,1,5,2,4; p06's seq 3 is sent twice; p08 is cut to its 4-token budget with finish_reason `length`. Policy: p04 and p12 allowed, p09 not. The server logs each request's path, body prompt_id, X-Request-Id and Authorization.

### 5. What does a baselines page look like?

`{"data": [...records...], "cursor": <the cursor that was sent, or null>, "next_cursor": <base64 cursor or null>}`. There are 13 records ordered oldest run first; some prompt ids have stray case or whitespace, and p05 appears twice (r1 then r2).

### 6. What does with_retries return and how are waits computed?

It calls `attempt(n)` with n starting at 1, and returns `(last_response, attempts_made)`. Between attempts it awaits `sleep(retry_delay(response, retries, policy))`; `retry_delay` returns the Retry-After header as float seconds if present, else `backoff_seconds * 2**retries`. Tests inject a sleep that records the delay and returns immediately.

### 7. How is an answer graded?

`grade` lower-cases and collapses whitespace in both the expected answer and the completion text, then checks that the expected string is a substring of the completion.
