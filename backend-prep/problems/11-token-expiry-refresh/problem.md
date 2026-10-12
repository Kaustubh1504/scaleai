# 11. Token expiry and refresh

A crawler walks every task on the labeling platform, one request at a time.
The Tasks API's access tokens live only **10 seconds** and each request takes
about **1 second**, so the crawl outlives many tokens. Security can also
revoke all tokens at any moment. Build a client that never sends an expired
token, doesn't hammer the token endpoint, and recovers from a revocation.

## The API

**Token**: `POST /oauth/token`, form-encoded (httpx `data=`). Always send
`client_id` and `client_secret`, plus one of:

```
grant_type=client_credentials
grant_type=refresh_token&refresh_token=<refresh_token>
```

```json
{"access_token": "tok_00001", "token_type": "bearer", "expires_in": 10, "refresh_token": "rt_00001"}
```

* Wrong client credentials → **401**. A bad/used/expired refresh token → **400** `invalid_grant`.
* Refresh tokens are **single-use**: each response has a new one.

**Data** (header `Authorization: Bearer <access_token>`; bad/expired token → **401**):

* `GET /v1/tasks/{task_id}` → `{"id": "task_0001", "status": "done", "priority": 1}` (404 if unknown)
* `GET /v1/tasks?page=&per_page=` → page envelope `{"data", "page", "per_page", "total", "total_pages"}`

## Setup

```python
from kit import FakeClock
from problem_api import make_api, CLIENT_ID, CLIENT_SECRET
clock = FakeClock(); http = make_api(clock).client()   # every request advances the fake clock by 1 s
```

The `if __name__ == "__main__":` block is what the Run button executes: get a
token by hand, make a dozen GETs while printing `clock.time()`, and try the
same refresh token twice.

## Your task

Your module must define:

* `class ApiError(Exception)`: `ApiError(status, path, message="")`; attributes
  `.status: int` and `.path: str`.
* `class AuthError(ApiError)`: same constructor; used for auth failures.
* `class ApiClient`: `ApiClient(http: httpx.Client, client_id: str, client_secret: str, clock)`
  where `clock` has `.time() -> float`; method `get(path: str, params: dict | None = None) -> dict`.

Rules:

* **Proactive refresh.** Before every data request, get a new token if you
  have none, or if it expires in **less than 2 seconds**. Compute expiry as
  `t + expires_in`, where `t = clock.time()` read **just before** you sent
  the token request (the server's clock is ahead of yours by the latency).
* **How to get a token.** If you hold a refresh token, use
  `grant_type=refresh_token` first; if that returns **400**, fall back to
  `client_credentials`. Without a refresh token, use `client_credentials`.
  Any other non-200 from the token endpoint → `AuthError`.
* **Reactive refresh.** If a data request returns **401**, get a new token
  (same procedure) and retry that same request **once**. A second 401 →
  `AuthError`.
* Other non-2xx → `ApiError` (no retry). Otherwise return the JSON body.
* Make no request in `__init__`, and never request a token you don't need.

## Example

```python
client = ApiClient(http, CLIENT_ID, CLIENT_SECRET, clock)
client.get("/v1/tasks/task_0001") ... client.get("/v1/tasks/task_0060")
# token at t=0 (expires t=10 by your math); GETs at t=1..8;
# at t=9 it expires in 1 s < 2 s: refresh (grant_type=refresh_token), and so on.
# 60 GETs, 8 token requests, zero 401s.
```

## Constraints

* Time comes from `clock.time()` only. Never `time.time()` / `time.sleep()`.
* Go through `http` only. Don't touch `api.issuer` or `api.issued`.

<details><summary>Hint 1</summary>

Keep `self._token`, `self._refresh_token` and `self._expires_at`. A
`_ensure_token()` called at the top of `get()` keeps the logic in one place.
</details>

<details><summary>Hint 2</summary>

Split `get()` into a helper that sends one request with the current token,
and the policy around it: send; on 401 renew the token and send once more;
on a second 401 raise.
</details>

## Follow-up (talk it through)

* Why subtract a safety margin from `expires_in`? What sets its size (latency, clock skew)?
* Ten threads share this client and the token expires. How do you avoid ten
  simultaneous token requests ("thundering herd")?
* Why is it dangerous to retry a `POST` after a 401 the same way?
