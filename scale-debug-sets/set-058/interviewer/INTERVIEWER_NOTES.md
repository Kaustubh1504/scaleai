# set-058 interviewer notes

**Scenario:** A month of API events is replayed through a per-tenant sliding-minute limiter (overrides, suspension via override 0, unlimited enterprise), then allowed units are invoiced with included units, round-up overage and credits. Test 3 is the finance statement.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Enterprise check compares the Plan enum to a string

1. **Nudge:** orbit is enterprise, so why is it throttled at all?
2. **Area:** Check what type tenant.plan is when limit_for compares it.
3. **Exact:** Compare enum to enum: tenant.plan is Plan.ENTERPRISE (drop .value).

### B2: Request exactly 60 s old still counted in the window

1. **Nudge:** kestrel's throttled time is 10:01:00. How far is that from its first request?
2. **Area:** Look at the eviction condition in apply_limit.
3. **Exact:** Evict when the age is >= WINDOW_S.

### B3: rpm_override 0 collapsed to None

1. **Nudge:** ivory should be suspended. What does tenants.csv say, and what does the Tenant object hold?
2. **Area:** Follow rpm_override from the CSV into limit_for.
3. **Exact:** Drop the `or None`; parse_int already returns None for blank.

### B4: Credit keys trimmed but not lower-cased

1. **Nudge:** delta-labs has a credit in credits.json. Why is credit_cents 0?
2. **Area:** Compare how tenant ids and credit keys are normalised.
3. **Exact:** Use norm_id(k) for the credit keys.

### B5: Overage part-cents floored instead of rounded up

1. **Nudge:** harbor is one cent short. Work its overage out by hand.
2. **Area:** Look at how overage_cents turns a fractional cent into an integer.
3. **Exact:** Use ceiling division: -(-overage * price // 1000).

### B6: Top tenants sorted quietest first

1. **Nudge:** top_tenants lists quill with 1 request. Does that match 'most requests first'?
2. **Area:** Look at the sort key for top.
3. **Exact:** Negate the count: key=lambda t: (-requests[t], t).

## "Why did that fix work?" probes

**B1**
- Would this comparison have worked if Plan subclassed str?
- Why didn't orbit's invoice change even though two requests were throttled?

**B2**
- Why did the 10:01:05 request flip from throttled to allowed?
- Why is kestrel's invoice unchanged?

**B3**
- Why does limit_for test `is not None` rather than truthiness?
- Why didn't sable (override 5) notice anything?

**B4**
- Why did harbor's and orbit's credits still apply?
- Where else could a silent .get(..., 0) fallback hide a lookup mismatch?

**B5**
- Why did delta-labs come out right?
- Why does -(-a // b) give a ceiling?

**B6**
- Why not just add reverse=True to the original key?
- Why does nimbus never appear here, even though it sent requests?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `meterbill/utils.py` → `parse_ts`: Treating an all-digit string as epoch seconds and calling fromtimestamp looks like a timezone trap, but it passes tz=timezone.utc, and the two text formats get tzinfo=UTC too, so every timestamp is aware UTC and they compare and subtract consistently (1777633210 is 2026-05-01 11:00:10 UTC).
