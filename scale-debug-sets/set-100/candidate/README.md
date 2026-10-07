# Relay Grade

A nightly eval harness for a chat model served behind a streaming **completion relay**.
For every prompt in the eval set it streams the model's answer, rebuilds the answer from
the relay's delta events, grades it against the expected answer, and compares the result
with the baseline scores of earlier runs to flag regressions. Some prompts must first be
cleared by the relay's policy service.

The client is plain `asyncio` with no HTTP library: `relaygrade/wire.py` speaks HTTP/1.1
over `asyncio.open_connection`, one request per connection. The tests run everything
against a scripted local relay in `tests/mock_server.py`.

The test suite is currently failing. Get it passing by correcting the source code, and be
ready to explain each change: what the symptom was, where it came from, and why.

## Data

- `data/config.json`: model name, concurrency limit, retry settings, baseline page size,
  default token budget and the `new_since` date.
- `data/suites.csv`: one row per suite with its owner and token budget (`max_tokens`).
- `data/prompts.csv`: the eval prompts (`prompt_id`, `suite`, `priority`, `review`,
  `added`, `prompt`, `expected`).

## Spec

This spec defines correct behaviour. If the code and the spec disagree, the spec wins.

### Loading

- Prompt ids: trim and lower-case (` P02 ` → `p02`). Suite names: trim and lower-case.
- Prompt text: collapse runs of whitespace. Rows whose prompt text is blank are ignored.
- `review` is true for `yes`, `y`, `true` or `1` (any case); anything else, including a
  blank cell, is false.
- `added` uses one of `2026-08-03`, `08/14/2026` (month/day/year) or `Aug 20 2026`.
- A prompt's token budget is its suite's `max_tokens`; a blank budget means
  `default_max_tokens` from the config. The model name is trimmed.
- Priority `1` is the most important. Prompts are dispatched in priority order, then by id.

### Streaming a prompt

1. A prompt with `review` true is first checked with `GET /v1/policy/<prompt_id>`. If the
   response says `"allowed": false` the prompt is **blocked**: it is not streamed and is
   listed under `blocked`. Prompts without `review` are never checked.
2. Otherwise the client sends `POST /v1/complete` with
   `{"model", "prompt_id", "prompt", "max_tokens", "stream": true}`. At most
   `max_concurrency` completion requests may be in progress at once.
3. Every completion request carries the API key (`Authorization: Bearer <key>`) and the
   header `X-Request-Id: <prompt_id>-<attempt>`, where attempt is 1 for the first try,
   2 for the first retry, and so on.
4. Statuses 429, 500, 502, 503 and 504 are retried, up to `max_retries` retries (so at
   most `max_retries + 1` attempts per prompt). Before retry *k* (k = 0 for the first
   retry) the client waits `Retry-After` seconds if the response has that header, or
   `backoff_seconds * 2**k` otherwise. Any other non-200 status is final.
5. A prompt whose final status is not 200 is **failed** with reason `HTTP <status>`.

### Rebuilding the answer

6. A 200 response is a chunked NDJSON stream. Each delta event is
   `{"seq": n, "delta": "..."}`; the last event is
   `{"done": true, "finish_reason": "...", "usage": {"completion_tokens": n}}`.
7. The relay may deliver deltas out of order and may resend a delta it has already sent.
   The answer is the deltas joined in `seq` order, each `seq` used once.
8. A stream that ends without a `done` event is **failed** with reason
   `stream ended before done`.

### Grading and regressions

9. An answer **passes** when the expected answer, lower-cased with whitespace collapsed,
   appears inside the answer normalised the same way.
10. Baselines come from `GET /v1/baselines?limit=<baseline_page_size>` and are cursor
    paginated: pass the page's `next_cursor` as `cursor` to get the next page, until
    `next_cursor` is null. Records are ordered oldest run first; a prompt's baseline is
    the score of its **most recent** record (baseline prompt ids are trimmed and
    lower-cased).
11. A **regression** is a prompt that has an answer this run, does not pass, and whose
    baseline score is 1. Prompts with no baseline, blocked prompts and failed prompts are
    never regressions.

### Report

`relaygrade.reports.build_report()` returns:

- `model`: the configured model name.
- `answers` / `finish_reasons`: prompt id → rebuilt answer / finish reason, for every
  prompt that produced an answer.
- `completion_tokens`: total `completion_tokens` over those answers.
- `passed`: sorted ids of answers that pass.
- `blocked`: sorted ids of blocked prompts.
- `failed`: prompt id → failure reason, for every failed prompt.
- `attempts`: prompt id → number of completion attempts made.
- `suites`: suite → `{"graded": answers in the suite, "passed": passing answers}`, for
  suites with at least one answer.
- `regressions`: sorted regression ids.
- `new_prompts`: sorted ids of prompts added on or after `new_since`.

## Running

Requires Python 3.10+. No third-party packages.

```bash
python main.py                         # print the report
python -m unittest discover -s tests   # run the tests
python -m pytest tests                 # same tests, if you have pytest
```

## Rules

- Do not modify the tests or anything under `data/`.
- Do not modify code marked `# VERIFIED`; it has been reviewed and is correct.
- Everything else is fair game. Each change should be small.
