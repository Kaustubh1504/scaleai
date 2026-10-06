# Judge Client

A batch client that sends question/answer pairs to an LLM "judge" endpoint, retries
transient failures, parses the judge's JSON verdict, and then pulls the per-request
usage records (paginated) to build a run summary.

The tests run against `tests/mock_server.py`, a local HTTP server that behaves like the
real endpoint (rate limits, 5xx errors, fenced JSON, paginated usage). It is test
infrastructure, so leave it alone.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Inputs

- `data/config.json`: model settings. Every key in it must be used exactly as given;
  defaults apply only to keys that are **missing**.
- `data/prompts.csv`: `request_id` (trim, lower-case), `question`, `answer`, `due`.
  Rows with a blank answer are not sent. `due` is `2026-05-01`, `05/01/2026`
  (month/day/year) or `May 1 2026`.
- Prompts are sent in order of `due` date, earliest first. Prompts with the same date
  keep their file order.

### Request

`POST {base_url}/v1/chat/completions` with headers `Authorization: Bearer <api_key>`
and `Content-Type: application/json`, and body:

```json
{
  "model": "<config.model>",
  "messages": [
    {"role": "system", "content": "<config.system_prompt>"},
    {"role": "user", "content": "Question: <question>\nAnswer: <answer>"}
  ],
  "max_tokens": <config.max_tokens>,
  "temperature": <config.temperature>,
  "metadata": {"request_id": "<request_id>"}
}
```

### Retries

- HTTP 429, 500, 502, 503 and 504 are transient. Retry them up to
  `config.max_retries` times, so there are at most `max_retries + 1` attempts in total.
- Between attempts, wait `Retry-After` seconds if the response has that header,
  otherwise `backoff_seconds × 2^attempt` (where `attempt` starts at 0).
- Any other status is final straight away.

### Result per request

- Final status ≥ 400 → `http_error` with that `http_status`. The body is not parsed.
- Status 200 → parse `choices[0].message.content`:
  - The verdict is a JSON object, possibly inside a ```` ```json ```` fence and possibly
    with prose around it. Objects can contain nested objects.
  - It must have `score` (a number from 0 to 10) and `passed`. `passed` is a JSON
    boolean or the string `"true"`/`"false"` (any case).
  - Anything that does not meet these rules → `parse_error`.
  - Otherwise → `ok` with `score` (float) and `passed` (bool).

### Usage and summary

- After all prompts are sent, read every usage record with `GET /v1/usage?limit=<page_size>`,
  then follow `next_cursor` (passed as `&cursor=`) until it is `null`. **Every** page's
  records count, including the last.
- `summary`:
  - `counts`: number of results per status (`ok`, `parse_error`, `http_error`);
  - `mean_score`: mean score of `ok` results, rounded to 2 decimals;
  - `pass_rate`: passed ÷ `ok` results, rounded to 3 decimals;
  - `total_tokens`: sum of `total_tokens` over all usage records;
  - `p50_latency_s`: median `latency_ms` over all usage records, **in seconds**,
    rounded to 3 decimals.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # run the batch against the bundled mock server
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests (including `tests/mock_server.py`) or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
