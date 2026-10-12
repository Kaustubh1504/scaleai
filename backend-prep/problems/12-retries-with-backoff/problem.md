# 12. Retries with exponential backoff

Your labeling pipeline calls the internal **Tasks API** thousands of times an
hour. It's flaky: load balancers throw the odd 502/503, connections drop, and
now and then a response is cut off halfway through the body. One blip
shouldn't kill a two-hour job. Write the retry helper the whole team will use.

## The API

* `GET /v1/tasks/{task_id}`: `{"id": "task_001", "kind": "transcribe", "priority": 1}`, or **404**.
* `POST /v1/tasks/{task_id}/labels` with JSON `{"label": "cat"}`: **201**, or **422** without a label.

Every successful response from this API has a JSON body. Faults you'll see:

| What happens | Example |
|---|---|
| 500 / 502 / 503 / 504 | `{"error": "service unavailable"}` |
| transport error | `httpx.ReadTimeout`, `httpx.ConnectError` (both are `httpx.TransportError`) |
| truncated body | status **200** but the body is `{"truncated": {"id": "ta` (not valid JSON) |

## Setup

```python
from problem_api import make_api
api = make_api(); client = api.client()      # httpx.Client wired to the mock
api.script("GET /v1/tasks/task_001", [503, "timeout", "malformed"])  # queue faults
```

`clock` is any object with `clock.time()` / `clock.sleep(s)`; tests pass a
`kit.FakeClock`, which records every wait in `clock.sleeps`. The
`if __name__ == "__main__":` block is what the Run button executes: use it to
print what each scripted fault actually looks like (status, `resp.text`,
which exception) before you handle it.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, path, attempts, message="")`;
  attributes `.status: int | None` (last HTTP status seen; `None` if the last
  attempt was a transport error), `.path: str` (the path you were given),
  `.attempts: int` (how many requests were made).
* `request_with_retries(client: httpx.Client, method: str, path: str, *, clock, rng: random.Random, max_attempts: int = 4, base_s: float = 0.5, cap_s: float = 8.0, **kwargs) -> httpx.Response`

Rules:

* Send with `client.request(method, path, **kwargs)`, so `params=`, `json=`,
  `headers=` etc. pass straight through, on every attempt.
* **Success**: a 2xx whose body parses as JSON. Return the response.
* **Transient** (retry): 500, 502, 503, 504, any `httpx.TransportError`, and a
  2xx whose body is not valid JSON.
* **Anything else** (400, 401, 404, 409, 422, 429, ...): don't retry. Raise
  `ApiError(status, path, attempts)` immediately.
* **Backoff**: after failed attempt `n` (1-based), if another attempt is left,
  sleep `clock.sleep(rng.uniform(d / 2, d))` where
  `d = min(cap_s, base_s * 2 ** (n - 1))`. Call `rng.uniform` exactly once per
  sleep and use `rng` for nothing else.
* Don't sleep before the first attempt or after the last one.
* If all `max_attempts` attempts are transient failures, raise `ApiError`
  with the last status (`200` if the last body was garbage, `None` if it was a
  transport error) and `attempts == max_attempts`.

## Example

```python
api = make_api()
api.script("GET /v1/tasks/task_001", [503, "timeout", "pass"])
resp = request_with_retries(api.client(), "GET", "/v1/tasks/task_001",
                            clock=clock, rng=random.Random(0))
resp.json()    # {"id": "task_001", ...}
clock.sleeps   # [0.461..., 0.878...]: one in [0.25, 0.5], one in [0.5, 1.0]
```

## Constraints

* Use `clock.sleep`, never `time.sleep`. Use `rng`, never the `random` module.
* Don't catch bare `Exception`: retry only what's listed.

<details><summary>Hint 1</summary>

Loop over attempt numbers 1..max_attempts with a `try/except httpx.TransportError`
around the request. Classify each outcome as *success / transient / fatal*,
and sleep at the bottom of the loop only when another attempt remains.
</details>

<details><summary>Hint 2</summary>

`resp.json()` raises `json.JSONDecodeError`, which is a `ValueError`. Check
for it inside the success branch.
</details>

## Follow-up (talk it through)

* Why jitter? What happens when 500 workers all retry at exactly 0.5 s, 1 s, 2 s?
* Retrying a `POST` that timed out: when is that safe, and when could it
  create a duplicate label? (See problem 15.)
* Where would you put an overall deadline, and how do retries interact with it?
