# set-069 interviewer notes

**Scenario:** Replay a request trace through a TTL cache in front of a guideline origin, keyed by project and locale, with client-specific labels added per response. Test 2 checks the payloads clients actually received.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Entry still fresh at exactly its TTL

1. **Nudge:** N3 is served version 1, but version 2 was published at 09:08. How old is the cached entry at N3?
2. **Area:** Look at the freshness comparison in TTLCache.get.
3. **Exact:** Use now < entry.expires_at.

### B2: Cache key ignores locale

1. **Nudge:** B2 asked for fr but was served locale en as a hit. Which entry did it hit?
2. **Area:** Look at how lookup builds the cache key.
3. **Exact:** The key must include the locale: (req['project'], req['locale']).

### B3: Cache hands out its stored object

1. **Nudge:** S4 comes from client c3, which has no overrides, yet it gets 'sarcasm'. Where did that label come from?
2. **Area:** lookup mutates value['labels']. Which object is that on a hit?
3. **Exact:** TTLCache.get should return copy.deepcopy(entry.value).

## "Why did that fix work?" probes

**B1**
- Why did N4 become a miss with the old comparison?
- The VERIFIED fetch uses <=. Why is that not the same mistake?

**B2**
- Why didn't the ner and sentiment results change?
- The origin fetch already takes a locale. Why wasn't that enough?

**B3**
- Why was S1 (a miss) never a problem, even without the copy on get?
- Would a shallow copy (dict(entry.value)) have been enough? Why not?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `guidecache/origin.py` → `GuidelineOrigin.fetch`: `published_at <= now` is the README rule ('at or before now'), so bbox en v2 (published 09:30) is correctly invisible during the trace while ner v2 (09:08) appears at N3. It returns a new dict with a copied label list, so callers can't mutate origin records.
