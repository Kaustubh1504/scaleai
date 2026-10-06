# shared/ — mock external services

Every problem uses these fakes instead of real networks. They run in-process
(fast, deterministic tests) or as real local HTTP servers (for curl-driven
demos during the interview). Python 3.10+, depends only on fastapi, uvicorn,
httpx and pydantic.

Problems import them through `candidate/mock_services/`, which puts this
directory's parent on `sys.path`. Keep `candidate/` inside `scale-backend-sets/`,
or use `python tools/export_candidate.py prob-XXX <dest>` to make a standalone copy.

| Module | What it fakes |
|---|---|
| `fake_clock` | `RealClock` / `FakeClock` with `time()`, `monotonic()`, `sleep()`, `asleep()`, `advance()`, `call_later()` |
| `tokens` | `count_tokens(text)`: one token per word run or punctuation char. All mocks bill with it. |
| `mock_llm` | An LLM: completion, tool calling, SSE streaming, with fault injection |
| `mock_worker` | Worker nodes that can be killed, slowed, go silent, or crash mid-task |
| `mock_webhook_receiver` | A webhook endpoint with scripted failures and HMAC signature checks |
| `mock_rest` | **The main API-client mock.** Configurable REST API: related resources, page/offset/cursor pagination, expiring OAuth tokens or API keys, 429 + Retry-After, random 5xx, timeouts, messy (nullable / inconsistently typed) nested fields, a results sink, deterministic seeds |
| `mock_api` | A smaller single-resource API (OAuth expiry, cursor pagination, flaky pages). Prefer `mock_rest` for new problems |

## fake_clock

Write time-dependent code against a clock object, never `time.time()` directly.

```python
clock = FakeClock(start=0)
clock.sleep(2.5)            # returns instantly; time is now 2.5; clock.sleeps == [2.5]
                            # (mock latency advances the clock but is not recorded in sleeps)
clock.call_later(5, fn)     # fn runs when time is advanced past 7.5
clock.advance(10)
```

## mock_llm

```python
from shared.mock_llm import MockLLMClient, LLMConfig, LLMError
client = MockLLMClient(LLMConfig(seed=7, failure_rate=0.1, fenced_rate=0.2))
resp = client.complete("Classify the ticket. <item>I was charged twice</item>", timeout=5)
resp.text            # '{"label": "billing", "confidence": 0.93}'
client.usage         # Usage(calls=1, failed_calls=0, input_tokens=..., output_tokens=..., cost_usd=...)
```

Same interface over HTTP: `HTTPLLMClient(base_url)` / `AsyncHTTPLLMClient`, and
`python -m shared.mock_llm --port 8001 [--failure-rate 0.1 ...]`. Async in-process
methods: `acomplete`, `achat`, `astream`.

### Methods

| Call | Returns |
|---|---|
| `complete(prompt, *, system=None, timeout=None)` | `LLMResponse(text, input_tokens, output_tokens, model)` |
| `chat(messages, *, tools=None, timeout=None)` | `ChatResponse(content, tool_calls=[ToolCall(id, name, arguments_json)], ...)` |
| `stream(prompt, *, system=None, timeout=None)` | iterator of text chunks; raises `LLMStreamInterruptedError` if dropped |

### Errors (all subclass `LLMError`; check `.retryable`)

| Exception | HTTP | Retryable | Notes |
|---|---|---|---|
| `LLMTimeoutError` | 504 | yes | also raised when latency exceeds your `timeout` |
| `LLMRateLimitError` | 429 | yes | `.retry_after` seconds (header `Retry-After`, rounded up) |
| `LLMServerError` | 500/502/503 | yes | also connection failures |
| `LLMBadRequestError` | 400 | no | |
| `ContextLengthExceededError` | 400 | no | prompt tokens > `max_context_tokens` |
| `LLMStreamInterruptedError` | – | yes | stream ended without `done` |

### Prompt conventions (built-in classifier)

* Single item: wrap the text in `<item>...</item>`. Instructions outside the tags are ignored.
  Answer: `{"label": "...", "confidence": 0.0-1.0}`.
* Batch: a JSON array of `{"id", "text"}` inside `<items>...</items>`.
  Answer: a JSON array of `{"id", "label", "confidence"}` in the same order.
* `KeywordClassifier(keywords, default_label)` decides the label; problems define their own keyword maps.
  Confidence is deterministic per text: 0.70–0.99 clear winner, 0.50–0.69 tie, 0.30–0.49 no keyword hit.

### Faults (`LLMConfig`)

At most one fault per call. Every random choice comes from
`Random(f"{seed}|{prompt_key}|{attempt}")`, where `attempt` counts sends of that
exact prompt, so results are reproducible even with concurrent calls.

| Field | Effect |
|---|---|
| `latency_s`, `latency_jitter_s` | added delay (on the clock) |
| `timeout_rate`, `timeout_hang_s` | hang, then `LLMTimeoutError` |
| `rate_limit_rate`, `retry_after_s` | random 429 |
| `rpm_limit`, `rate_limit_window_s` | deterministic limit: N successful calls per window, then 429 with exact `retry_after` |
| `failure_rate` | 500/502/503 |
| `wrong_label_rate` | a label outside the allowed set (`"unknown"`, `"N/A"`, `"Billing Issue"`) |
| `inconsistent_rate` | a different *valid* label than the true one |
| `malformed_rate` | truncated JSON or single-quoted pseudo-JSON (not recoverable) |
| `fenced_rate` | the JSON wrapped in a ```` ```json ```` fence (recoverable) |
| `prose_wrapped_rate` | the JSON surrounded by chatty prose (recoverable by extracting the object) |
| `tool_loop_rate` / `tool_bad_args_rate` / `tool_unknown_rate` | chat: repeat the previous tool call / truncated JSON arguments / tool name + `_v2` |
| `stream_disconnect_rate` | stream stops early without `done` |
| `max_context_tokens` | reject long prompts with HTTP 400 |
| `fault_script={3: "timeout"}` | force a fault on global call #3 (1-based) |
| `prompt_faults={"T-17": ["timeout", "fenced"]}` | the 1st call whose prompt contains `T-17` times out, the 2nd is fenced, later ones are clean (counted per substring, so rewording a retry prompt does not reset it) |
| `fail_first_attempts=N` | every distinct prompt fails its first N attempts |
| `input_cost_per_1k`, `output_cost_per_1k` | pricing (default $0.50 / $1.50 per 1k tokens) |

Usage counters: successful calls are billed for input + output tokens; failed
calls are counted in `failed_calls` and not billed.

### Tool calling

`ScriptedAgent({"weather": [ToolStep("get_weather", {"city": "SF"}), FinalStep("Sunny.")]})`
picks the script whose key appears in the first user message, and advances one
step per `tool` message in the history. Message format:

```python
{"role": "user", "content": "..."}
{"role": "assistant", "content": None, "tool_calls": [{"id": "...", "name": "...", "arguments": "<json>"}]}
{"role": "tool", "tool_call_id": "...", "content": "..."}
```

### HTTP server

`POST /v1/complete`, `POST /v1/chat`, `POST /v1/stream` (SSE: `event: delta` …
`event: done`), `GET /v1/usage`, `POST /v1/admin/reset`, `PATCH /v1/admin/config`
(change any `LLMConfig` field live — handy for "now the model starts failing"),
`GET /health`.

## mock_rest

```python
from shared.mock_rest import MockRestAPI, AuthConfig, RateLimitConfig, FaultConfig, ResourceConfig, FieldMess
api = MockRestAPI.scale(seed=7, clock=clock,                     # Scale-flavoured preset
                        auth=AuthConfig(token_ttl_s=60),
                        rate_limit=RateLimitConfig(requests=10, window_s=1),
                        faults=FaultConfig(seed=7, failure_rate=0.05))
http = api.client(timeout=5)       # httpx.Client over an in-process transport (api.async_client() too)
api.canonical("tasks")             # clean ground truth; api.rendered("tasks") = what the wire shows
api.canonical("results")           # what the client POSTed to the results sink
api.log                            # every request: method, path, params, status, clock time, outcome
```

Run it for real: `python -m shared.mock_rest --port 9300 --seed 7 --rate-limit 10/1 --failure-rate 0.05`.

**Preset resources** (`scale_resources(seed)`; sizes configurable):

| resource | pagination (params) | envelope | filters | nested route |
|---|---|---|---|---|
| projects | page (`page`, `per_page`) | `results, page, per_page, total, total_pages` | status, customer.id, task_type | |
| annotators | offset (`offset`, `limit`) | `items, offset, limit, total` | country, level, is_active | |
| tasks | cursor (`cursor`, `limit`) | `data, next_cursor` | project_id, status, is_gold | `/v1/projects/{id}/tasks` |
| submissions | cursor | `data, next_cursor` | task_id, annotator_id | `/v1/tasks/{id}/submissions` |
| reviews | page | `results, ...` | reviewer_id, verdict, submission_id | `/v1/submissions/{id}/reviews` |
| results | page; **writable** (`POST /v1/results`, `Idempotency-Key`) | | | |

All list endpoints accept `?updated_since=<ISO-8601>`. Nested objects: `project.customer`,
`project.settings`, `task.payload.dimensions`, `submission.answer.boxes[]`.

**Custom APIs**: `MockRestAPI([ResourceConfig("orders", records, pagination="offset",
envelope={"data": "rows"}, filters=("status",), parent=("customers", "customer_id"),
mess=[FieldMess("total", ["str", "null"], 0.2)])], ...)`.

**Custom actions** for state-changing endpoints: `MockRestAPI(..., actions={("POST",
"/v1/tasks/{id}/claim"): fn})` where `fn(api, request, params, identity) -> (status, body)`
runs after auth, rate limiting and faults (use `api.records(name)` for the live data).

**Field mess** (`FieldMess(path, variants, rate)`) is decided per record from the seed, so a
record always looks the same. Variants: `null`, `missing`, `str`, `float`, `epoch`,
`epoch_ms`, `iso_naive`, `iso_offset`, `csv`, `bool_int`, `bool_str`, `upper`, `lower`,
`padded`, `empty_str`, `wrap` (`{"value": v}`), `list`. Paths are dotted; `boxes[].label`
reaches into lists.

**Pipeline per request**: auth → rate limit → faults → latency → route.

| Behaviour | Details |
|---|---|
| Auth (`oauth`) | `POST /oauth/token` with `client_id`/`client_secret` (JSON or form) → `access_token`, `expires_in`, single-use `refresh_token` (`grant_type=refresh_token`). 401 `{"error": "missing_token" \| "invalid_token" \| "token_expired"}`. `max_requests_per_token` kills a token early. Modes `api_key` (`X-API-Key`) and `none`. `api.expire_all_tokens()`, `api.revoke_refresh_tokens()` |
| Rate limit | sliding window per client (refreshing a token does not reset it) or global; 429 with `Retry-After` as seconds, HTTP-date (with a `Date` header to compare against) or omitted; `X-RateLimit-*` headers |
| Random faults | `failure_rate` (500/502/503), `rate_limit_rate`, `malformed_rate` (200 + truncated JSON), `slow_rate`/`latency_s` (→ `httpx.ReadTimeout` when over the client's timeout). Drawn per (seed, method+path+query, attempt): retrying a URL gets a new draw |
| Scripted faults | `FaultConfig(scripted={"GET /v1/tasks?cursor": [503, "429:3", "timeout", "malformed"]})`: successive matching requests get these outcomes |
| Pagination | cursor is keyset-based (stable when records are inserted mid-crawl); offset/page shift like real APIs. `api.insert()` / `api.update()` / `on_request=` hook to mutate data during a crawl. Bad params → 400 |

## mock_worker

```python
w = MockWorker("w1", capacity=4, latency_s=0.2, clock=clock)
w.process(task, timeout=1.0)   # result, or WorkerUnreachableError / WorkerTimeoutError / WorkerOverloadedError / TaskFailedError
w.kill(); w.slow(10); w.go_silent(); w.revive(); w.crash_on_next(); w.die_after(3)
MockWorker("w2", crash_if=lambda task: task.get("poison"))   # poison jobs kill it (WorkerCrashedError)
w.heartbeat()                  # {"worker_id", "in_flight", "capacity", "ts"} or None if dead/silent
fleet = WorkerFleet([w], clock=clock, interval_s=1.0); fleet.run(5, sink=lb.on_heartbeat)
```

`worker_transport({"http://w1": w1})` gives an `httpx.MockTransport` (dead →
`ConnectError`, silent → `ReadTimeout`). `python -m shared.mock_worker --id w1
--port 9001 --heartbeat-url ...` runs a real one; `POST /admin/kill` exits the process.

## mock_webhook_receiver

```python
r = WebhookReceiver(secret="whsec", clock=clock)
r.script_event("evt_1", [500, "timeout", "429:5", 200])
client = httpx.Client(transport=r.transport())
r.accepted_event_ids(); r.attempts_for("evt_1"); r.deliveries[-1].signature_valid
```

Signature header: `X-Webhook-Signature: t=<unix>,v1=<hex hmac_sha256(secret, f"{t}." + body)>`
(`sign()` / `verify_signature()`). Event ids come from the `X-Event-Id` header or the JSON `id` field.

## mock_api

```python
api = MockRecordsAPI(records, clock=clock, token_ttl_s=60, rpm_limit=10)
api.script_page(20, [500, "429:3"])   # page starting at offset 20: 500, then 429, then OK
api.expire_all_tokens()
client = httpx.Client(transport=api.transport(), base_url="http://api")
```

`POST /oauth/token`, `GET /v1/records?limit=&cursor=` → `{"data", "next_cursor"}`,
`GET /v1/records/{id}`. 401 `token_expired` after the TTL.

## Tests

`python -m pytest shared/tests` from `scale-backend-sets/`.
