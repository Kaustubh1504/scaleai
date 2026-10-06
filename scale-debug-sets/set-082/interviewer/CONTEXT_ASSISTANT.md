# set-082 context questions for an AI assistant

Use these to practise asking an assistant for **context** (what a file or function does,
where a value comes from, what the data looks like) rather than for the fix. The answers
describe what the candidate repo's code does. They don't say whether it is correct.

Interviewers: if the candidate has an assistant, questions like these are fair game.
"What's wrong with this?" or "Fix test 2" is not.

### 1. What does build_report do, in order?

It loads plans, tenants and the request log (`load_requests` also returns the skipped ids), resolves each tenant's `(limit, window_s)` with `effective_limit`, replays the log with `limiter.replay`, builds invoices from the accepted requests, applies credits, and assembles the report dict.

### 2. How does load_requests classify rows?

It normalises the tenant id and skips the row as `unknown_tenant` if the tenant isn't registered. Then it calls `parse_units` and `parse_ts` inside a `try`, and any `ValueError` puts the request id in `malformed`. Both lists are sorted at the end.

### 3. What does SlidingWindow keep, and what does offer return?

A deque of timestamps of accepted requests. `offer(ts)` first evicts timestamps at or before the cutoff it computes, then accepts if the deque is shorter than the limit and returns `(True, None)`, or else `(False, hint)` where the hint is computed from the oldest timestamp still in the deque.

### 4. In what order does replay process requests?

It processes all tenants' requests in one pass over `timeparse.chronological(requests)`, and each tenant uses its own SlidingWindow. The timeline records ids in that same order.

### 5. How is an invoice's subtotal computed?

`build_invoices` sums units per (tenant, UTC month) for billed plans, then sets `subtotal_cents = monthly_fee_cents + tiered_cents(blocks_for(usage, plan), plan.tiers)` and `total_cents = apply_discount(subtotal, discount_pct)`.

### 6. What type is discount_pct and where is it parsed?

A `Decimal`, parsed by `loader.parse_discount`, which strips whitespace and a trailing `%` and returns `Decimal(0)` for blank.

### 7. How do credits interact with totals?

`apply_credits` walks credits in file order, finds the invoice for `(tenant_id, month)`, and adds `min(amount, total - credits so far)` to `credits_cents`. Credits with no invoice are returned as unapplied ids.
