# set-045 interviewer notes

**Scenario:** Replay a quote-request trace through a TTL cache (per-model TTLs, 0 = never cache) in front of a time-versioned price origin, with per-tenant discounts. Report hits, prices, origin calls, per-tenant spend and the requests that were served stale prices.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Cache key ignores region

1. **Nudge:** R03 (m-small, eu) is a hit at 0.40. Which entry did it come from?
2. **Area:** Which request fields go into the cache key, and which of them change the origin price?
3. **Exact:** cache_key should return (model, region).

### B2: Entry still served at its exact expiry instant

1. **Nudge:** R10 is a hit. When was its entry stored, and what is m-large's TTL?
2. **Area:** Look at the freshness comparison in TTLCache.get.
3. **Exact:** Use `now < entry.expires_at`.

### B3: TTL of 0 replaced by the default

1. **Nudge:** R13 is a hit, but m-embed is configured never to be cached.
2. **Area:** Follow how quote() decides the TTL for m-embed.
3. **Exact:** Use self.ttls.get(model, self.default_ttl) so that 0 is kept.

## "Why did that fix work?" probes

**B1**
- Why is tenant correctly not part of the key here?
- Why did the expiry-boundary problem stay invisible until this was fixed?

**B2**
- Why didn't R10's price change even though its hit/miss status did?
- With region missing from the key, why did R10 no longer land on a boundary?

**B3**
- Why didn't any price change?
- Which other falsy values could a config like this contain, and how would you treat them?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `cachekit/origin.py` → `price_at`: `start <= at` is right: a price takes effect at its effective_from instant, so a request at exactly 10:03:00 sees the new price. `start >= best[0]` keeps the latest effective row, and on a tie the later file row wins, which never happens in this data.
