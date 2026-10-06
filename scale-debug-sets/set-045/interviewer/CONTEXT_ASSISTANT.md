# set-045 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do for each request?

It normalises the row in `load_requests` (blank region → `default_region`), calls `service.quote(tenant, model, region, at)`, records hit and price, updates the tenant totals, and adds the request id to `stale_served` when the returned `base` differs from `origin.price_at(...)` at that time.

### 2. What does QuoteService.quote return?

A dict with `hit` (whether the cache returned a value), `base` (the undiscounted price in the value) and `price` (base × (1 − tenant discount), rounded to 4 decimals). On a miss it fetches from the origin and caches the value when the model's TTL is above 0.

### 3. How is a model's TTL chosen?

`ttl_for` reads the model's entry from config `ttl_seconds`, with `default_ttl_seconds` (60) as the fallback. The config gives m-small 300, m-large 120 and m-embed 0. `quote()` only calls `cache.put` when the TTL it gets is above 0.

### 4. When does TTLCache.get treat an entry as expired?

It compares `now` with the entry's `expires_at` (stored time + TTL). If the entry fails the freshness comparison it is deleted and None is returned; otherwise a `dict(...)` copy of the stored value is returned.

### 5. What does PriceOrigin.fetch count and return?

Each call adds 1 to `origin.calls` and returns a new dict `{model, region, price}`, with the price from `price_at` for that instant. `origin_calls` in the report is this counter.

### 6. What does the price data look like?

prices.csv has one row per (model, region, effective_from). m-small/us changes from 0.50 to 0.60 at 10:03:00 and m-large/eu from 2.20 to 2.40 at 10:06:00. Model and region values are trimmed and lower-cased on load.
