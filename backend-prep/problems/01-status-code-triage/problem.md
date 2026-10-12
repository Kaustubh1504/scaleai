# 01. Status code triage

Your team's task-sync worker talks to five internal services (tasks,
annotators, payouts, ...). Every failure ends up in one log line and an
on-call engineer has to decide: *was it us or them, and should the worker
retry?* You're writing the one function that makes that call, so the whole
worker behaves consistently.

## Input

An HTTP method (`"GET"`, `"post"`, ...: compare case-insensitively), an
integer status code, and whether the request carried an **idempotency key**
(a client-generated id the server uses to de-duplicate repeated requests).

## Setup

Nothing to fetch: this is a pure function. Write everything in your file;
the `if __name__ == "__main__":` block is what the Run button executes, so
use it to print `triage(...)` for a few cases and compare them to the table.

## Your task

Your module must define:

* `ACTIONS`: a set of the ten action strings `"ok"`, `"fix_request"`,
  `"reauthenticate"`, `"forbidden"`, `"not_found"`, `"conflict"`,
  `"fix_payload"`, `"back_off"`, `"retry"`, `"give_up"`.
* `@dataclass(frozen=True) class Triage`: fields, in this order,
  `blame: str` (`"none"` | `"client"` | `"server"`), `retryable: bool`,
  `action: str` (one of `ACTIONS`). Tests build `Triage(blame, retryable, action)`
  positionally and compare with `==`.
* `triage(method: str, status: int, idempotency_key: bool = False) -> Triage`

**Step 1: classify the status.**

| status | blame | action | retryable? | why |
|---|---|---|---|---|
| 200, 201, 204, any other 2xx | none | `ok` | no | success |
| 400 | client | `fix_request` | no | malformed request: same bytes, same answer |
| 401 | client | `reauthenticate` | no | missing/expired credentials: refresh the token, don't blindly resend |
| 403 | client | `forbidden` | no | authenticated but not allowed: retrying never helps |
| 404 | client | `not_found` | no | the resource isn't there |
| 409 | client | `conflict` | no | clashes with current state (duplicate, version mismatch): re-read first |
| 422 | client | `fix_payload` | no | well-formed JSON, but fails validation |
| 429 | client | `back_off` | **yes\*** | you're sending too fast: wait (`Retry-After`), then retry |
| 500, 502, 503, 504, any other 5xx | server | `retry` | **yes\*** | their problem, often transient |
| any other 4xx | client | `fix_request` | no | |
| anything else (1xx, 3xx, < 100, > 599) | | | | raise `ValueError` |

**Step 2: the method rule (\*).** Retrying is only safe if doing the request
twice has the same effect as doing it once.

* `GET`, `HEAD`, `OPTIONS`, `PUT`, `DELETE` are **idempotent**: the table applies as is.
* Every other method (`POST`, `PATCH`, ...) is **non-idempotent**:
  * with `idempotency_key=True`: the table applies as is (the server de-duplicates).
  * without a key: **429 stays retryable** (`back_off`): a rate limiter
    rejects the request *before* any work happens. A **5xx becomes
    `retryable=False, action="give_up"`**: the server may have created the
    payout before it crashed, and a blind retry could pay someone twice.
    `blame` stays `"server"`.

## Example

```python
triage("GET", 503)                         # Triage("server", True,  "retry")
triage("POST", 503)                        # Triage("server", False, "give_up")
triage("POST", 503, idempotency_key=True)  # Triage("server", True,  "retry")
triage("post", 429)                        # Triage("client", True,  "back_off")
triage("DELETE", 418)                      # Triage("client", False, "fix_request")
triage("GET", 302)                         # ValueError
```

## Constraints

* Pure function, no HTTP. Return a `Triage`, never a bare tuple.
* Keep it readable: an interviewer should be able to check your rules against
  the table at a glance (think lookup dict + a couple of `if`s, not 40 branches).

<details><summary>Hint 1</summary>

A dict `{400: ("client", False, "fix_request"), ...}` for the specific codes,
then fall back on the class: `status // 100` is 2, 4 or 5.
</details>

<details><summary>Hint 2</summary>

Apply the method rule last, as a downgrade: if the result is retryable,
the status is 5xx, the method isn't idempotent and there's no key, return
`Triage("server", False, "give_up")`.
</details>

## Follow-up (talk it through)

* A `POST /payouts` times out with **no response at all**. Which row is that
  closest to, and what would you do?
* Why is `PUT` idempotent but `PATCH` usually not? Give an example of each.
* The 401 says your token expired. Where in the client should the refresh
  happen, and how do you stop two threads refreshing at once?
