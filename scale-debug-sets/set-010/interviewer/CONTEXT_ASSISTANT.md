# set-010 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report() call, and in what order?

`config.load_config` returns the billing period and Tenant objects (each holding its Plan). `limiter.replay` runs over `loader.load_requests`. `loader.load_usage` feeds `usage.monthly_tokens` and `usage.by_endpoint`. `billing.invoice` runs per tenant on its monthly tokens, and `report.top_tenants` ranks the invoices.

### 2. What units does the limiter work in?

`ts_ms` is an int in milliseconds as read from requests.csv, and `WINDOW_MS` is 60 000. The window filter and the retry-after value are both computed from those numbers inside `replay`.

### 3. Which requests go into the `allowed` lists in replay?

Only requests that were not throttled: the else branch appends `req.ts_ms` to that tenant's list. `recent` is rebuilt from that list for each request.

### 4. How is a tenant's discount_pct decided?

`load_config` parses the raw value with `_pct`, which returns None for null, missing or blank strings and a float otherwise, then picks between that value and the plan's `default_discount_pct` when building the Tenant.

### 5. What does by_endpoint do with the rows?

It keeps rows inside the billing period, groups them with `itertools.groupby` on `(tenant, endpoint)`, sums each group's tokens into `out[tenant][endpoint]`, and returns the dicts sorted by key.

### 6. How is an invoice computed?

`invoice` takes excess = tokens minus included_tokens (floored at 0), converts it to a number of 1k blocks, multiplies by overage_per_1k, adds base_fee, applies discount_pct, and rounds overage, discount and total to 2 decimals.

### 7. What does in_period compare?

`start <= row.day < end`, where `period_bounds` returns the first day of the billing month and the first day of the following month.
