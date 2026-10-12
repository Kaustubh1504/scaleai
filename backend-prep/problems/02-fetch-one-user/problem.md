# 02. Fetch one user safely

The payouts service looks up an annotator's profile before it pays them.
Today it calls the Users API with a bare `client.get(...).json()`: a 404's
error body gets treated as a profile, a slow Users API hangs the job, and
someone once passed a user id of `"../admin"`. Write the one helper
everybody should use instead.

## The API

`GET /v1/users/{user_id}`

```json
200 {"id": "u_001", "email": "ada@labelco.test", "role": "annotator", "active": true}
404 {"error": "user 'u_404' not found"}
```

Any other status (500, 503, ...) is a failure. The network can also fail
outright: httpx raises `httpx.TimeoutException` / `httpx.ConnectError`, both
subclasses of **`httpx.TransportError`**.

## Setup

```python
from problem_api import make_api, recording_client
api = make_api()
client = recording_client(api)   # an httpx.Client (default timeout 30 s) that records per-request timeouts
```

`api.script("GET /v1/users/u_001", [503, "timeout"])` makes the next calls to
that route return 503, then time out. The `if __name__ == "__main__":` block
is what the Run button executes: use it to print raw responses first.

## Your task

Your module must define:

* `class UserApiError(Exception)`: constructor `UserApiError(status, path, message="")`;
  attributes `.status: int | None` (HTTP status, `None` when no response came
  back) and `.path: str` (e.g. `"/v1/users/u_001"`).
* `get_user(client: httpx.Client, user_id: str) -> dict | None`

Rules:

* Validate `user_id` **before** making any request: it must be a `str` of
  1–64 characters, each a letter, digit, `_` or `-`. Otherwise raise
  `ValueError` (so `""`, `"../admin"`, `"a/b"`, `"u 1"`, `"u?x=1"` are all rejected).
* Send `GET /v1/users/{user_id}` through `client` with **`timeout=5`** on the
  request (the client's own default is different).
* **200**: return the parsed JSON dict. **404**: return `None` (a missing
  user is a normal answer, not an error).
* Any other non-2xx: raise `UserApiError(status, path)`.
* `httpx.TransportError`: raise `UserApiError(None, path)` **chained** to the
  original (`raise ... from exc`), so `err.__cause__` is the httpx exception.

## Example

```python
get_user(client, "u_001")     # {"id": "u_001", "email": "ada@labelco.test", ...}
get_user(client, "u_404")     # None
get_user(client, "../admin")  # ValueError, and no request was sent
```

## Constraints

* Go through HTTP only (don't read `USERS` / `api.users`).
* Don't catch bare `Exception`: catch what you mean.

<details><summary>Hint 1</summary>

`resp.raise_for_status()` raises `httpx.HTTPStatusError` for any 4xx/5xx,
which is handy but also turns your normal 404 into an exception. It's often
clearer to check `resp.status_code == 404` first, then `resp.is_success`,
and raise your own error. Callers shouldn't have to know you use httpx.
</details>

<details><summary>Hint 2</summary>

`re.fullmatch(r"[A-Za-z0-9_-]{1,64}", user_id)`. Why validate instead of
URL-encoding? `"../admin"` encodes to a different path on some servers and
proxies; rejecting it is simpler and safer for an id that has a known shape.
</details>

## Follow-up (talk it through)

* Why return `None` for 404 but raise for 503? Who decides, and what would
  the caller do differently?
* What does `raise ... from exc` buy you when this shows up in a log at 3 a.m.?
* `timeout=5`: is that connect, read, or total? What would you set for a
  payout job vs. a user-facing request?
