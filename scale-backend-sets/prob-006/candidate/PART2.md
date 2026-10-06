# Part 2: Long crawls and customer rollups (about 20 minutes)

In production the crawl takes longer than a token lives: tokens are issued with
`expires_in` of a few seconds and every request takes noticeable time. The
report must still complete. Account managers also want a per-customer view.

## Token lifecycle

* **Before** each `/v1` request: if there is no token, or the token expires in
  less than **5 seconds** by the client's `clock` (counting `expires_in` from
  when you requested the token), get a new one first. With this rule a crawl
  never sends an expired token.
* **Getting a new token**: if you hold a refresh token, use
  `grant_type=refresh_token`; if that fails with 400, fall back to the client
  credentials. A non-200 answer to the client-credentials request raises
  `AuthError`.
* **On a 401** from a `/v1` request (a token can also be revoked early): get a
  new token and retry that same request once. If the retry is also 401, raise
  `AuthError`. Never retry a 401 more than once per request.

## Customer rollup

Add a `customers` list to the report: one entry per customer that owns at least
one project, sorted by `customer_id`:

```json
{"customer_id": "cus_01", "customer_name": "Acme Robotics", "tier": "enterprise",
 "projects": 3, "tasks_total": 140, "tasks_completed": 70, "completion_rate": 0.5}
```

`completion_rate` follows the same rule as for projects (computed from the
customer's summed counts). The customer fields come from each project's nested
`customer` object.

Write tests that run a crawl with a short TTL and request latency, for example
`make_api(token_ttl_s=10, latency_s=1.0, clock=clock)` with a `FakeClock`, and
one where tokens are revoked mid-crawl (`api.expire_all_tokens()` from an
`on_request` hook, or between pages).
