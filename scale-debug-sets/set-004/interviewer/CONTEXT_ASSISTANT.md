# set-004 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does run_batch do?

It loads `config.json` into a frozen `Config`, builds a `ModelClient`, loads the prompts (blank answers dropped, sorted by due date), calls `client.grade` for each one in order, and then calls `collect_usage` to page through `/v1/usage`. `reports.build_report` turns the results and usage into the report dict.

### 2. Why does transport.send catch urllib.error.HTTPError?

`urllib` raises HTTPError for any 4xx/5xx response. The exception carries the status code, headers and body, so `send` converts it into the same `Response` object a 2xx produces. Callers always get a Response and decide what the status means.

### 3. How does send_with_retries decide to retry and how long to wait?

A response whose status is in `RETRYABLE` (429, 500, 502, 503, 504) is retried. Any other status is returned straight away. Before the next attempt it sleeps `wait_time(...)`: the `Retry-After` header if present, otherwise `backoff_seconds * 2**attempt`. When the loop ends it returns the last response.

### 4. What does parse_completion accept as a valid verdict?

It reads `choices[0].message.content`, and a missing key or index returns None. `extract_json` uses the fenced block if there is one, slices out the brace-delimited object and runs `json.loads` on it. The result must be a dict containing `score` and `passed`, with score between 0 and 10. `passed` goes through `_as_bool`, which accepts strings case-insensitively.

### 5. What does the mock server send for r05 and r07?

r05 always gets HTTP 400 with `{"error": {"message": "prompt too long"}}`. r07 always gets 503: the last scripted step repeats for every further attempt. r03 gets three 429s with `Retry-After: 0`, then a 200.

### 6. How does the usage endpoint paginate?

`GET /v1/usage?limit=N[&cursor=...]` returns `{"data": [...], "next_cursor": ...}`. The cursor is a base64-encoded offset, and `next_cursor` is `null` on the final page. Usage records are only created for 200 completions, in the order they were served.

### 7. Where do config defaults live?

As module constants at the top of `config.py` (`DEFAULT_MAX_TOKENS`, `DEFAULT_TEMPERATURE`, etc.), used inside `load_config` when it builds the `Config`.
