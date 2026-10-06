# set-093 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does replay() do with the two logs?

It builds one event list of `(ts, kind, position, event)` tuples, where kind is 0 for invalidations and 1 for requests, and sorts it on the first three fields. Invalidations call `cache.invalidate_sku`; requests go through `serve`, whose Response is appended to the result list.

### 2. What happens inside serve() on a miss?

It calls `origin.fetch(endpoint, sku, region, currency)`. If that raises UnknownPrice it returns an `error` Response. Otherwise it calls `cache.put(key, quote, req.ts)`. For `quote` requests it then sets `quote["price"]` to the discounted, rounded price and returns it.

### 3. What does origin.fetch return, and what does it count?

A new dict with endpoint, sku, region, currency and price, built from the prices table. Before the lookup, every call appends the SKU to `origin.calls`, including calls that end in UnknownPrice.

### 4. How does TTLCache pick the TTL for an entry?

`ttl_for(key)` reads `key[0]` (the endpoint) from the ttls dict loaded from ttl.json, and falls back to `ttls["default"]`.

### 5. How does invalidate_sku find the entries to remove?

It collects every key whose second element (`k[1]`, the SKU) matches, then deletes those keys from `_entries`.

### 6. Where are the summary numbers computed?

`reports.summarize` counts outcomes with a Counter, takes the min and max request `ts` from the loaded requests for the span, counts `origin.calls` per SKU, and divides the number of responses by the span for requests_per_hour.
