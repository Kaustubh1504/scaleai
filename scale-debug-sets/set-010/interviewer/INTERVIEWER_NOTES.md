# set-010 interviewer notes

**Scenario:** Replay a request sample through a per-tenant sliding-window limiter (retry-after in seconds), aggregate a month of metered token usage, and price invoices with per-1k overage blocks and plan-default discounts.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Retry-after left in milliseconds

1. **Nudge:** R07 should be able to retry in 35 seconds. What number do you get, and what unit is it?
2. **Area:** Look at how replay computes the retry-after value.
3. **Exact:** Divide the millisecond difference by 1000.

### B2: Request exactly 60 s old still counted

1. **Nudge:** R03 is throttled. Look at initech's timestamps.
2. **Area:** Compare the window test in replay with README rule 2.
3. **Exact:** Use `req.ts_ms - t < WINDOW_MS`.

### B3: groupby over unsorted rows

1. **Nudge:** by_endpoint is too low for acme chat, but monthly_tokens is right. How do the two differ?
2. **Area:** Look at how by_endpoint groups rows.
3. **Exact:** Sort the rows by (tenant, endpoint) before calling groupby.

### B4: Explicit 0% discount replaced by plan default

1. **Nudge:** umbrella has a discount, but config.json says 0. Where is the discount decided?
2. **Area:** Look at how load_config falls back to the plan's default.
3. **Exact:** Use `pct if pct is not None else plan.default_discount_pct`.

### B5: Overage blocks rounded instead of ceiled

1. **Nudge:** Only acme's overage is off, by one block's price. What is acme's excess?
2. **Area:** Look at how invoice turns excess tokens into blocks.
3. **Exact:** Use math.ceil(excess / 1000).

### B6: Top tenants sorted ascending

1. **Nudge:** The 'top' tenants have the smallest totals.
2. **Area:** Look at the sort key in top_tenants.
3. **Exact:** Negate the total: `(-kv[1]["total"], kv[0])`.

## "Why did that fix work?" probes

**B1**
- Why did the list of throttled requests stay right?
- How would naming the variable `retry_after_ms` vs `_s` have helped here?

**B2**
- Why did no other tenant change?
- What test data would you add to pin down both sides of this boundary?

**B3**
- Why are initech and wonka still right with the bug?
- How would a defaultdict(int) with `+=` avoid the problem altogether?

**B4**
- Why is tyrell (also 0) unaffected?
- Why did umbrella stay in the top three anyway?

**B5**
- What would round() do for an excess of 500 500 tokens?
- Why is it safer to bill in integer blocks than to multiply the raw excess by a per-token price?

**B6**
- Why negate the total instead of passing reverse=True here?
- With reverse=True, what would happen to the tenant-id tie-break?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `meterbill/usage.py` → `in_period`: `row.day < end` looks like it drops the last day of the month, but `end` from period_bounds is the first day of the next month, so 30 April is included and 1 May is not.
- `meterbill/loader.py` → `parse_day`: It accepts exactly the two date formats in the README, with month/day order for the slash format.
