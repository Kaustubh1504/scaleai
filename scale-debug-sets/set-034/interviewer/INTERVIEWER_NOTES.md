# set-034 interviewer notes

**Scenario:** Replay a day of per-tenant API requests through a sliding-window limiter (plan limits, overrides, 0 = suspended), tally allowed/billable usage, and invoice overage tokens with half-up cent rounding.

## Timeline

| Minutes | Phase |
|---|---|
| 0-6 | Orient: read README spec and data, skim layout, run the tests. |
| 6-50 | Debug: Test 1 -> Test 2 -> Test 3; expect ~7 min per bug. |
| 50-60 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Window left in milliseconds

1. **Nudge:** acme's 10:03 request is throttled though the previous ones are minutes old. How long does the window seem to be?
2. **Area:** Check the units of Plan.window against what age_seconds returns.
3. **Exact:** load_plans must divide window_ms by 1000.

### B2: Request exactly one window old counted as inside

1. **Nudge:** acme now throttles a04 instead of a05. How far apart are a01 and a04?
2. **Area:** Read rule 3 about the window boundary, then the filter in allow().
3. **Exact:** Use `age_seconds(ts, prev) < window`.

### B3: Override of 0 falls back to the plan limit

1. **Nudge:** t-echo has a limit_override. What does README rule 1 say it means?
2. **Area:** Look at how effective_limit chooses between the override and the plan.
3. **Exact:** Return `plan.limit if override is None else override`.

### B4: timedelta.seconds drops the days

1. **Nudge:** bolt's b06 and b07 are a full day after its other traffic. Why would they be throttled?
2. **Area:** Look at how the age of a previous request is computed.
3. **Exact:** Use `.total_seconds()`, not `.seconds`.

### B5: Endpoint counter shared by every tenant

1. **Nudge:** Every tenant shows the same endpoint counts. Where does each tenant's counter come from?
2. **Area:** Look at the attributes of TenantUsage.
3. **Exact:** Create the Counter in __init__: self.by_endpoint = Counter().

### B6: Banker's rounding on invoice amounts

1. **Nudge:** bolt and gale are each one cent short. What are their unrounded amounts?
2. **Area:** Look at how charge() rounds to the cent.
3. **Exact:** Use amount.quantize(CENT, rounding=ROUND_HALF_UP).

## "Why did that fix work?" probes

**B1**
- Why was bolt's next-day traffic unaffected by this?
- Where else would you look for unit mismatches in this codebase?

**B2**
- Why was this invisible while the window was in milliseconds?
- fern's f06 is also exactly 60 s after f02, yet it wasn't affected. Why?

**B3**
- Why did t-cove's override of 2 work even with this code?
- What would a blank override have produced if the code used `int(text or 0)`?

**B4**
- What would `.seconds` return for a negative timedelta of -10 seconds?
- Why did all of the other tenants come out right?

**B5**
- Why do allowed/throttled/billable_tokens behave correctly as class attributes?
- Would by_endpoint = {} at class level behave differently?

**B6**
- Why were acme, cove and dune unaffected?
- Would float arithmetic have given 2.93 for gale? Why or why not?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `meterbill/usage.py` → `billable`: It looks like it should exclude 4xx responses as well, but README rule 5 bills client errors and only drops 5xx, so `status < 500` is exactly the rule. tally() only calls it for allowed requests.
