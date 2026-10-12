# 05. Explore an unknown API via OpenAPI

The support lead wants to know, right now, **which customer has the most open
tickets**, so an account manager can call them before they churn. The
helpdesk vendor's API has no docs page, only its machine-readable spec. You've
never used this API before: that's the point. In the interview this is the
first ten minutes: find the endpoints, the auth, the pagination, *then* code.

## The API

All you're told:

* Base URL: `https://api.example.test` (`client` already has it).
* `GET /openapi.json` returns the OpenAPI 3 spec. It needs no auth.
* Your API key is passed in as `api_key`. *How* to send it is in the spec
  (look at `components.securitySchemes`).

Fetch and read the spec first: find which endpoints you need, how each one
paginates, what its limits are, and which endpoints you should ignore.

## Setup

```python
from problem_api import make_api, API_KEY
client = make_api().client()          # httpx.Client with the base URL set
spec = client.get("/openapi.json").json()
```

`make_api(seed=0, n_customers=23)` takes other seeds/sizes for different
datasets. The `if __name__ == "__main__":` block is what the Run button
executes: pretty-print the spec there (`json.dumps(spec, indent=2)`) and hit
each endpoint once before writing the function.

## Your task

Your module must define:

* `customer_with_most_open_tickets(client: httpx.Client, api_key: str) -> dict | None`

Rules:

* Send `api_key` on every `/v1` request the way the spec's security scheme says.
* Return `{"customer_id": int, "name": str, "open_tickets": int}` for the
  customer with the most tickets whose status is exactly `"open"`.
* Tie: the **smallest `customer_id`** wins.
* No open tickets at all: return `None`.
* You must read **every** page of whatever you list: results span several pages.
* Customers with zero tickets exist; they must not break anything.
* Any non-2xx response: call `resp.raise_for_status()` (raises `httpx.HTTPStatusError`).

## Example

Customers 4 (Globex) and 9 both have 6 open tickets, more than anyone else
(`make_api(top_ids=(4, 9))`) → `{"customer_id": 4, "name": "Globex", "open_tickets": 6}`.

## Constraints

* Go through HTTP only: don't read `api.customers` / `api.tickets` or the
  internals of `problem_api.py`. Pretend it's a vendor's server.
* Respect the limits the spec states (page sizes). Out-of-range values are a 400.
* Keep requests reasonable: no request per ticket.

<details><summary>Hint 1</summary>

Explore in the Run block before writing the function: list the paths, look
at each list endpoint's `parameters`, and at `components.securitySchemes`.
Then hit each endpoint once and print the raw response. Note anything
marked `deprecated`.
</details>

<details><summary>Hint 2</summary>

Two different pagination styles: customers use `page`/`per_page` with
`total_pages`; tickets use `limit`/`cursor` with `next_cursor`. The tickets
endpoint can filter by status server-side, so you only need the open ones.
Count per customer (a `Counter`), then pick the highest count, breaking
ties by smallest id: `max(counts.items(), key=lambda kv: (kv[1], -kv[0]))`.
</details>

<details><summary>Hint 3</summary>

You need names for only one customer. Is there an endpoint for a single
customer, or do you page through all of them? Both are fine; say which you'd
pick and why.
</details>

## Follow-up (talk it through)

* Walk the interviewer through how you explored the API. What would you do
  if there were no OpenAPI spec at all?
* Counting via `?customer_id=` per customer vs. one pass over all open
  tickets: how many requests does each make for 10k customers?
* The answer changes while you're paginating (tickets get opened and closed).
  How much does that matter for this report?
