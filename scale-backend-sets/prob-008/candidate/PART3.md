# Part 3: Publishing payouts safely (about 20 minutes)

Finance now wants the payouts pushed to the results sink (`POST /v1/results`,
see `API.md`) instead of a CSV they upload by hand. Money is involved, so a run
must never pay anyone twice, and the API is having a bad week: transient 5xx
errors, slow responses, the occasional truncated body, and rate limiting.

## Retries (apply to every request: token, GETs and POSTs)

* Every request uses `timeout=10` seconds.
* **Transient failures**: HTTP 500, 502, 503, any `httpx.TransportError`
  (including timeouts), and a 2xx response whose body is not valid JSON.
  A request gets at most **4 attempts**. Before attempt `n + 1` wait (with
  `clock.sleep`) a random duration drawn uniformly from `[d / 2, d]` where
  `d = min(8, 0.5 * 2 ** (n - 1))` seconds. If all 4 attempts fail, raise `ApiError`.
* **429**: wait the number of seconds in `Retry-After` (1 second if the header
  is missing), then send the request again. 429s do **not** use up the 4
  attempts, but after **10** 429s in a row for the same request, raise `ApiError`.
* Other 4xx responses are not retried (a 401 from the token endpoint is still `AuthError`).

## Publishing

```python
from earnings.payouts import publish_payouts

outcome = publish_payouts(client, report)   # report: what compute_earnings returned
# -> {"published": ["ann_001", ...], "failed": ["ann_007"]}
```

* An annotator is **payable** when their row has `on_hold: false` and
  `earnings_cents > 0`. Nobody else is posted.
* For each payable annotator, in row order, send
  `POST /v1/results` with body
  `{"annotator_id": <id>, "period": <report["period"]>, "amount_cents": <earnings_cents>}`
  and header `Idempotency-Key: payout:<period>:<annotator_id>`
  (e.g. `payout:2024-04-01T00:00:00Z/2024-04-15T00:00:00Z:ann_001`).
* A `201` (stored) or `200` (replay of an earlier run) means **published**.
* If an annotator's POST still fails after the retry policy (or gets a 4xx),
  record them under **failed** and carry on with the next annotator. Errors
  obtaining a token (`AuthError`) propagate.
* `published` and `failed` list annotator ids in row order.
* Running the same period twice must not create any new results.

Add a `--publish` flag to the CLI that publishes after writing the CSV and
prints what was published and what failed.

Write tests with scripted faults, for example
`FaultConfig(scripted={"POST /v1/results": ["malformed", 503]})` (a "malformed"
POST was stored by the sink even though you never saw the answer), and check
`api.canonical("results")`, `api.log` and `clock.sleeps`.

## Discussion (no code required)

Be ready to talk about:

* money correctness: why integer cents, where rounding is allowed and who it
  favours, and how you would reconcile what you published against the sink and
  against finance's ledger;
* exactly-once payouts: what the idempotency key does and does not guarantee
  (what if the amount changes between two runs of the same period?), and
  at-least-once delivery vs exactly-once effect;
* monitoring data quality: how you would notice next month that a new wire
  format appeared or that unknown rewards doubled, before anyone is underpaid.
