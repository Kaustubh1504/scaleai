# set-093 interviewer notes

**Scenario:** Replay a two-day request log and invalidations through a TTL cache keyed on (endpoint, sku, region, currency), in front of a pricing service. Quote responses get a per-client discount that must not leak into the cache. Test 2 summarises hits, origin calls and traffic rate.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Cache key leaves out the currency

1. **Nudge:** r04 asked for GBP but got 40.0, the EUR price. Where could that number come from?
2. **Area:** Compare the key used to look up the cache with README rule 3.
3. **Exact:** request_key must include req.currency: (req.endpoint, req.sku, req.region, req.currency).

### B2: Cache stores the caller's dict, which the discount then mutates

1. **Nudge:** birch has no discount, yet r02 was charged 90.0, acme's price. How could acme's discount reach birch?
2. **Area:** Follow the `quote` dict on a miss: origin → cache.put → discount. Who else holds a reference to it?
3. **Exact:** put() must store a copy: Entry(dict(value), now).

### B3: Log span uses timedelta.seconds

1. **Nudge:** The log runs from 20 Sep 08:00 to 21 Sep 09:30. How many hours is that?
2. **Area:** Look at how span_hours is computed from the two datetimes.
3. **Exact:** Use (last - first).total_seconds() / 3600.

## "Why did that fix work?" probes

**B1**
- Why did the summary's hit and miss counts not change, even though two requests were served differently?
- Why did the price fetched on a miss still come out in the right currency?

**B2**
- Why is get() already safe, and why isn't that enough here?
- Would dict(value) still be enough if the quote held a nested dict (say, a tax breakdown)?

**B3**
- Why does the cache's own age check not suffer from this?
- For what log lengths would .seconds give the right answer?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `quotecache/cache.py` → `get`: `age < ttl` looks like it should be `<=`, but the spec says an entry is stale at exactly the TTL (r10, at exactly 3600 s, must miss). It uses total_seconds(), so day-old entries are seen as stale, and it returns a copy.
- `quotecache/loader.py` → `parse_ts`: The `/ 1000` looks like a ms-vs-s slip, but the numeric timestamps really are milliseconds and fromtimestamp takes seconds. It converts in UTC and drops the tzinfo so the values compare with the naive UTC strings.
