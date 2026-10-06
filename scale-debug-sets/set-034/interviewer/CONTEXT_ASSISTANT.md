# set-034 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What order does build_report() run things in?

It loads plans, then tenants (resolving each tenant's limit with effective_limit), then requests for known tenants. `limiter.run` returns an allowed/throttled decision per request id, `usage.tally` builds a TenantUsage per tenant, and `billing.invoice` turns each usage into an invoice. `billing.total` sums the amounts.

### 2. What units is Plan.window in, and where is it set?

The dataclass comment says seconds. It is set in `plans.load_plans` from the plan's `window_ms` value in plans.json.

### 3. How does SlidingWindowLimiter.allow decide?

It takes the tenant's stored list of previously allowed timestamps, keeps those whose `age_seconds(ts, prev)` passes the window comparison, and throttles if the kept list has at least `tenant.limit` entries. Otherwise it appends `ts` and stores the kept list as the new history.

### 4. In what order does run() feed requests to the limiter?

`sorted(requests, key=lambda r: r.ts)`. Python's sort is stable, so equal timestamps keep the order they were loaded in.

### 5. What does TenantUsage hold?

Class-level defaults for `allowed`, `throttled` and `billable_tokens`, plus the attributes set in `__init__`. `tally` increments the counters and the per-endpoint counts for each request.

### 6. How is an invoice amount computed?

`overage` subtracts the plan's included tokens (floored at 0) and `charge` multiplies by `price_per_1k` as a Decimal, divides by 1000 and rounds to cents. The report converts the Decimal to a string.

### 7. Where does price_per_1k come from when plans.json has it as a JSON number?

`load_plans` does `Decimal(str(spec["price_per_1k"]))`, so 0.15 becomes Decimal('0.15') rather than the binary float's expansion.
