# set-021 interviewer notes

**Scenario:** Replay a request log against a TTL cache that sits in front of a model server handing out pre-labels per (task, model, locale). Publishes bump the model version and flush that model. Test 2 checks the JSON report.

## Timeline

| Minutes | Phase |
|---|---|
| 0-3 | Orient: read README spec, skim layout, run the tests. |
| 3-25 | Debug: work Test 1 then Test 2; expect ~7 min per bug. |
| 25-30 | Explain: candidate walks through each fix (symptom, location, why, fix). |

Hand out hints only when the candidate has been stuck on the same symptom for ~4 minutes,
and give one level at a time. Record every hint on the scoring sheet.

## Hint ladders

### B1: Cache key drops the locale

1. **Nudge:** Look at the 09:02:00 ocr fetch. What locale was asked for, and what locale is in the value returned?
2. **Area:** How is the cache key built for a fetch?
3. **Exact:** make_key returns (task_id, model); it needs (task_id, model, locale).

### B2: Entry still served at its exact expiry

1. **Nudge:** Compare the seg fetches at 09:02:30 and 09:03:00 with the TTL for seg-v2.
2. **Area:** Read README cache rule 3, then look at how freshness is checked on lookup.
3. **Exact:** TTLCache.get uses now <= entry.expires_at; it should be now < entry.expires_at.

### B3: last_refresh dumped via str() instead of ISO

1. **Nudge:** Compare the last_refresh strings with the other timestamps in the JSON.
2. **Area:** How does each timestamp field in build_report get turned into a string?
3. **Exact:** last_refresh needs iso(s.last_refresh) if s.last_refresh else None.

## "Why did that fix work?" probes

**B1**
- Why did the bad hit disappear after the 09:06:00 publish?
- The CacheEntry stores locale too. Why doesn't that protect the lookup?

**B2**
- purge_expired uses <= and is correct. Why are the two comparisons opposite?
- Why did the 09:03:00 fetch change from hit to miss, even though it isn't on a boundary?

**B3**
- Why didn't json.dumps raise on a datetime here?
- Would test_last_refresh have caught this if it read build_report() instead of report_json()? What would it show?

## If the candidate edits a `# VERIFIED` region

Stop them and ask them to show, from the spec and the data, why it is wrong. These regions are correct:

- `labelcache/store.py` → `purge_expired`: `expires_at <= now` looks like the opposite boundary from get(), but it is the same rule seen from the other side: an entry is expired at exactly t + T, so purge must remove it when expires_at == now.
