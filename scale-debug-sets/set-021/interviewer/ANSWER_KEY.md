# set-021 answer key: Pre-label TTL cache replay

**Domain:** cache_ttl  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_lookups.TestLookups.test_ocr_lookups` | B1 Cache key drops the locale |
| `test_1_lookups.TestLookups.test_seg_lookups` | B2 Entry still served at its exact expiry |
| `test_2_cache_report.TestCacheReport.test_last_refresh` | B3 last_refresh dumped via str() instead of ISO |

## Failing pattern with all bugs present

- `tests.test_1_lookups.TestLookups.test_ocr_lookups`
- `tests.test_1_lookups.TestLookups.test_seg_lookups`
- `tests.test_2_cache_report.TestCacheReport.test_last_refresh`

## Bugs (recommended order)

### B1: Cache key drops the locale

- **Type:** cache-key-missing-param
- **Symptom:** test_ocr_lookups fails: the 09:02:00 fetch for T01 fr-fr comes back as ('hit', 'ocr-v1@1/T01/en-us') instead of ('miss', 'ocr-v1@1/T01/fr-fr'), and the 09:04:00 fr-fr fetch also returns the en-us value.
- **Location:** `labelcache/service.py` → `make_key`
- **Why it fails:** The key is only (task, model), so T01's fr-fr fetch finds the en-us entry and serves the English pre-label as a hit. README rule 1 says locale is part of the identity.
- **Failing test:** `test_1_lookups.TestLookups.test_ocr_lookups`
- **Unblocks:** test_ocr_lookups

Fix:

```diff
-    return (req.task_id, req.model)
+    return (req.task_id, req.model, req.locale)
```

Observed with only this bug applied (`tests.test_1_lookups.TestLookups.test_ocr_lookups`):

```
AssertionError: Lists differ: [('09[140 chars]r', 'hit', 'ocr-v1@1/T01/en-us'), ('09:04:00',[339 chars]jp')] != [('09[140 chars]r', 'miss', 'ocr-v1@1/T01/fr-fr'), ('09:04:00'[340 chars]jp')]

First differing element 2:
('09:02:00', 'T01', 'fr-fr', 'hit', 'ocr-v1@1/T01/en-us')
('09:02:00', 'T01', 'fr-fr', 'miss', 'ocr-v1@1/T01/fr-fr')

Diff is 928 characters long. Set self.maxDiff to None to see it ...
```

### B2: Entry still served at its exact expiry

- **Type:** time-window-boundary
- **Symptom:** test_seg_lookups fails: the 09:02:30 seg-v2 fetch for T02 is a 'hit' instead of a 'miss', and the 09:03:00 fetch then flips from hit to miss.
- **Location:** `labelcache/store.py` → `TTLCache.get`
- **Why it fails:** seg-v2 has a 120 s TTL; the entry stored at 09:00:30 expires at 09:02:30, and the fetch at exactly 09:02:30 must miss. `<=` treats the expiry instant as still fresh, so it hits, the entry is not refreshed, and the 09:03:00 fetch then misses instead of hitting.
- **Failing test:** `test_1_lookups.TestLookups.test_seg_lookups`
- **Unblocks:** test_seg_lookups

Fix:

```diff
-        if now <= entry.expires_at:
+        if now < entry.expires_at:
```

Observed with only this bug applied (`tests.test_1_lookups.TestLookups.test_seg_lookups`):

```
AssertionError: Lists differ: [('09[81 chars]s', 'hit', 'seg-v2@1/T02/en-us'), ('09:03:00',[341 chars]us')] != [('09[81 chars]s', 'miss', 'seg-v2@1/T02/en-us'), ('09:03:00'[341 chars]us')]

First differing element 1:
('09:02:30', 'T02', 'en-us', 'hit', 'seg-v2@1/T02/en-us')
('09:02:30', 'T02', 'en-us', 'miss', 'seg-v2@1/T02/en-us')

Diff is 654 characters long. Set self.maxDiff to None to see it.
```

### B3: last_refresh dumped via str() instead of ISO

- **Type:** json-serialization
- **Symptom:** test_last_refresh fails: every last_refresh comes out as '2026-03-02 09:15:30' (space) instead of '2026-03-02T09:15:30'.
- **Location:** `labelcache/reports.py` → `build_report`
- **Why it fails:** The raw datetime goes into the report, and report_json's default=str turns it into '2026-03-02 09:15:30' with a space. The spec wants the ISO 'T' form that every other timestamp uses.
- **Failing test:** `test_2_cache_report.TestCacheReport.test_last_refresh`
- **Unblocks:** test_last_refresh

Fix:

```diff
-                "last_refresh": s.last_refresh,
+                "last_refresh": iso(s.last_refresh) if s.last_refresh else None,
```

Observed with only this bug applied (`tests.test_2_cache_report.TestCacheReport.test_last_refresh`):

```
AssertionError: {'ner-v3': '2026-03-02 09:15:30', 'ocr-v1': '2026-03-02 09:12:0[31 chars]:30'} != {'ner-v3': '2026-03-02T09:15:30', 'ocr-v1': '2026-03-02T09:12:0[31 chars]:30'}
- {'ner-v3': '2026-03-02 09:15:30',
?                       ^

+ {'ner-v3': '2026-03-02T09:15:30',
?                       ^

-  'ocr-v1': '2026-03-02 09:12:00',
?                       ^

+  'ocr-v1': '2026-03-02T09:12:00' ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `labelcache/store.py` → `purge_expired`: `expires_at <= now` looks like the opposite boundary from get(), but it is the same rule seen from the other side: an entry is expired at exactly t + T, so purge must remove it when expires_at == now.
