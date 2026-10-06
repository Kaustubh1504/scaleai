# set-082 interviewer notes

**Scenario:** Replay a gateway log through per-tenant sliding-window rate limiters (half-open window, retry hints), then bill accepted units per UTC month in whole 1,000-unit blocks with graduated tiers, a percentage discount rounded half-up, and capped account credits.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Unparseable units swallowed as 0

1. **Nudge:** Which two rows should be malformed, and where do they end up instead?
2. **Area:** Follow how load_requests decides a row is malformed, then look at the helper it calls for units.
3. **Exact:** parse_units must let the ValueError propagate (drop the try/except or re-raise).

### B2: Same-instant requests re-ordered by id

1. **Nudge:** The garnet requests that swap places share something. What?
2. **Area:** Look at the sort key used before replay.
3. **Exact:** Sort on r.ts only; Python's sort is stable and keeps file order for ties.

### B3: Window treated as closed at t − W

1. **Nudge:** How far apart are elm-labs' first accepted request and the extra rejected one?
2. **Area:** Look at how expired timestamps are evicted from the window.
3. **Exact:** Evict while accepted[0] <= cutoff.

### B4: Retry hint drops fractional seconds

1. **Nudge:** The hints that differ are each off by less than a second. Which tenant's timestamps have fractions?
2. **Area:** Look at how elapsed time is measured for the hint.
3. **Exact:** Use .total_seconds(), not .seconds.

### B5: Partial blocks dropped

1. **Nudge:** Which subtotals are too low, and what do their billable units have in common?
2. **Area:** Look at how billable units are turned into blocks.
3. **Exact:** Round up: -(-billable // BLOCK_UNITS) (or math.ceil(billable / BLOCK_UNITS)).

### B6: Half-cent discount rounded to even

1. **Nudge:** acme is one cent short. Work out 5050 less 15% by hand.
2. **Area:** Look at how the discounted amount is rounded.
3. **Exact:** Quantize with ROUND_HALF_UP instead of round().

## "Why did that fix work?" probes

**B1**
- Why didn't the invoices change even though two extra requests were replayed?
- What could have gone wrong for a tenant close to its rate limit?

**B2**
- Why is the request id a poor tie-breaker for this log?
- When would this ordering change which request gets rejected?

**B3**
- Why does no invoice change?
- Which data point would you add to catch the opposite mistake?

**B4**
- Why is elm-labs' 3.0 hint correct even with .seconds?
- Besides fractions, when else does .seconds differ from total_seconds()?

**B5**
- Why was acme's subtotal right?
- How does -(-a // b) compute a ceiling?

**B6**
- Which other values would round() and ROUND_HALF_UP disagree on?
- Why does nobody else's total change?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `meterbill/timeparse.py` → `parse_ts`: It looks like it might drop offsets or choke on the trailing Z, but it rewrites Z as +00:00, lets fromisoformat handle the ISO/space forms (including fractions and offsets), falls back to the month/day slash format, assumes UTC when there is no offset and converts to UTC. That is exactly what pushes cinder's 00:30+01:00 request into February.
- `meterbill/plans.py` → `tiered_cents`: The floor/ceiling bookkeeping looks fragile, but each tier charges the blocks between the previous tier's limit and min(blocks, its own limit), stops once the usage fits, and treats null as unbounded. 56 blocks on growth is 50 x 25 + 6 x 18 = 1358.
