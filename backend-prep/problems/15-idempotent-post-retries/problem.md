# 15. Idempotent POST retries

At the end of each week you pay customers' refunds and annotator bonuses
through a **Payments API**. Retrying a `GET` is harmless. Retrying a `POST`
that timed out **may charge twice**: the server might have stored the payment
before the connection died. The API supports an **`Idempotency-Key`** header
so retries are safe, but only if you use it correctly.

## The API

`POST /v1/payments` with JSON `{"order_id": "ord_1001", "amount_cents": 2599}`
and header `Idempotency-Key: <key>` (required, else **400**).

| Situation | Response |
|---|---|
| new key | **201** `{"id": "pay_0001", "order_id": "ord_1001", "amount_cents": 2599, "status": "succeeded"}` |
| same key, same body | **200**, the *stored* payment, header `Idempotent-Replayed: true` |
| same key, different body | **409** |
| invalid body (e.g. `amount_cents <= 0`) | **422** |

Faults to expect: 5xx; `timeout` / `connect` errors **before** the server saw
the request; a truncated 2xx body (`malformed`) **after** it stored the
payment; and a timeout **after** it stored the payment
(`api.timeout_after_commit` in the mock).

## Setup

```python
from problem_api import make_api
api = make_api(); client = api.client()
api.script("POST /v1/payments", [api.timeout_after_commit, "malformed", 503, "timeout"])
```

`api.payments` (dict id -> payment) shows what was really charged: look at it
while exploring, never in your solution. `clock` is anything with
`clock.time()` / `clock.sleep(s)`; tests pass a `kit.FakeClock`, which records
waits in `clock.sleeps`. The `if __name__ == "__main__":` block is what the
Run button executes: post the same key twice (and with a different amount)
there to see a replay and a 409.

## Your task

Your module must define:

* `class PaymentError(Exception)`: constructor `PaymentError(status, order_id, message="")`;
  attributes `.status: int | None`, `.order_id: str`.
* `class IdempotencyConflictError(PaymentError)`: the 409 case (same constructor and attributes).
* `pay(client: httpx.Client, order_id: str, amount_cents: int, *, clock, rng: random.Random, max_attempts: int = 5, base_s: float = 0.5, cap_s: float = 8.0) -> dict`

Rules:

* Send `POST /v1/payments` with body `{"order_id", "amount_cents"}` and
  `Idempotency-Key: pay:<order_id>` (exactly that, e.g. `pay:ord_1001`). The key
  comes from the order, never random, so re-running the whole script is safe too.
* Return the payment dict from the 200/201 body.
* Transient (retry with the **same key and same body**): 500/502/503/504, any
  `httpx.TransportError`, a 2xx whose body isn't valid JSON. Back off as in
  problem 12: after failed attempt `n`, if attempts remain,
  `clock.sleep(rng.uniform(d / 2, d))` with `d = min(cap_s, base_s * 2 ** (n - 1))`.
* **409**: raise `IdempotencyConflictError(409, order_id)` right away.
* Any other 4xx: raise `PaymentError(status, order_id)` right away.
* Out of attempts: raise `PaymentError` with the last status (`None` after a
  transport error).

## Example

```python
api.script("POST /v1/payments", [api.timeout_after_commit, "malformed"])
pay(client, "ord_1001", 2599, clock=clock, rng=random.Random(0))
# 3 requests, all with Idempotency-Key: pay:ord_1001
# -> {"id": "pay_0001", "order_id": "ord_1001", "amount_cents": 2599, "status": "succeeded"}
len(api.payments)   # 1: charged once
```

## Constraints

* Go through HTTP only. Don't read `api.payments` in your solution.
* Use `clock.sleep` and `rng`, never `time.sleep` or the `random` module.

<details><summary>Hint 1</summary>

Build `headers` and `body` **once**, before the retry loop, and reuse the
same objects on every attempt.
</details>

<details><summary>Hint 2</summary>

Why not `uuid4()` for the key? Think about the script crashing after the
payment and being run again tomorrow.
</details>

## Follow-up (talk it through)

* The server forgets idempotency keys after 24 h. What does that mean for a
  job that retries the next day?
* A teammate wants to change the amount on a payment that 409s. What do you
  tell them?
* What would *you* store client-side so a crash mid-batch can resume without
  re-sending everything?
