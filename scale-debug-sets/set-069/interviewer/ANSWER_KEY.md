# set-069 answer key: Guideline TTL cache: expiry boundary, cache key, shared payloads

**Domain:** cache_ttl  |  **Length:** MINI  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_lookups.TestLookups.test_ner_lookups` | B1 Entry still fresh at exactly its TTL |
| `test_1_lookups.TestLookups.test_bbox_lookups` | B2 Cache key ignores locale |
| `test_2_report.TestReport.test_sentiment_payloads` | B3 Cache hands out its stored object |

## Failing pattern with all bugs present

- `tests.test_1_lookups.TestLookups.test_bbox_lookups`
- `tests.test_1_lookups.TestLookups.test_ner_lookups`
- `tests.test_2_report.TestReport.test_sentiment_payloads`

## Bugs (recommended order)

### B1: Entry still fresh at exactly its TTL

- **Type:** time-window-boundary
- **Symptom:** Test 1 test_ner_lookups: N3 is ('hit', 1) instead of ('miss', 2), N4 becomes ('miss', 2) and N5 ('hit', 2). The 600 s boundary falls on N3 and N5.
- **Location:** `guidecache/cache.py` → `TTLCache.get`
- **Why it fails:** The README says an entry is fresh while age < ttl, so at exactly 600 s it has expired. With `<=`, N3 (09:10:00, exactly 600 s after N1) is served the stale v1 instead of fetching v2, and the miss/hit pattern after it shifts.
- **Failing test:** `test_1_lookups.TestLookups.test_ner_lookups`
- **Unblocks:** test_ner_lookups.

Fix:

```diff
-        if now <= entry.expires_at:
+        if now < entry.expires_at:
```

Observed with only this bug applied (`tests.test_1_lookups.TestLookups.test_ner_lookups`):

```
AssertionError: {'N1'[25 chars]t', 1), 'N3': ('hit', 1), 'N4': ('miss', 2), 'N5': ('hit', 2)} != {'N1'[25 chars]t', 1), 'N3': ('miss', 2), 'N4': ('hit', 2), 'N5': ('miss', 2)}
  {'N1': ('miss', 1),
   'N2': ('hit', 1),
-  'N3': ('hit', 1),
-  'N4': ('miss', 2),
?    ^

+  'N3': ('miss', 2),
?    ^

-  'N5': ('hit', 2)}
?    ^             ^

+  'N4': ('hit', 2),
?    ^             ^

+  'N5': ('mis ...
```

### B2: Cache key ignores locale

- **Type:** cache-key-missing-param
- **Symptom:** Test 1 test_bbox_lookups: B2 (fr) is ('hit', 1, 'en') instead of ('miss', 1, 'fr'), and B4 (fr) is served locale 'en'.
- **Location:** `guidecache/service.py` → `GuidelineService.lookup`
- **Why it fails:** Keyed by project only, the French bbox request B2 hits the English entry cached by B1 a minute earlier, so a French client gets English labels.
- **Failing test:** `test_1_lookups.TestLookups.test_bbox_lookups`
- **Unblocks:** test_bbox_lookups.

Fix:

```diff
-        key = req["project"]
+        key = (req["project"], req["locale"])
```

Observed with only this bug applied (`tests.test_1_lookups.TestLookups.test_bbox_lookups`):

```
AssertionError: {'B1'[24 chars]': ('hit', 1, 'en'), 'B3': ('hit', 1, 'en'), '[42 chars]en')} != {'B1'[24 chars]': ('miss', 1, 'fr'), 'B3': ('hit', 1, 'en'), [43 chars]en')}
  {'B1': ('miss', 1, 'en'),
-  'B2': ('hit', 1, 'en'),
?          ^ ^       ^^

+  'B2': ('miss', 1, 'fr'),
?          ^ ^^       ^^

   'B3': ('hit', 1, 'en'),
-  'B4': ('hit', 1, 'en'),
?                    ^^

+  'B4': ('hit ...
```

### B3: Cache hands out its stored object

- **Type:** aliasing-shallow-copy
- **Symptom:** Test 2 test_sentiment_payloads: S2 through S5 all show ['positive', 'negative', 'neutral', 'sarcasm', 'sarcasm']. Every sentiment hit shares the cached list, which acme's two hits appended to. Only S1 (miss) and S6 (fresh miss) are correct.
- **Location:** `guidecache/cache.py` → `TTLCache.get`
- **Why it fails:** lookup appends override labels to the value it got back. If get returns the cached object itself, acme's 'sarcasm' is appended to the cache entry, so later hits from other clients see it and acme gets it twice.
- **Failing test:** `test_2_report.TestReport.test_sentiment_payloads`
- **Unblocks:** test_sentiment_payloads.

Fix:

```diff
-            return entry.value
+            return copy.deepcopy(entry.value)
```

Observed with only this bug applied (`tests.test_2_report.TestReport.test_sentiment_payloads`):

```
AssertionError: {'S1'[85 chars]tral', 'sarcasm', 'sarcasm'], 'S3': ['positive[216 chars]al']} != {'S1'[85 chars]tral'], 'S3': ['positive', 'negative', 'neutra[150 chars]al']}
  {'S1': ['positive', 'negative', 'neutral', 'sarcasm'],
-  'S2': ['positive', 'negative', 'neutral', 'sarcasm', 'sarcasm'],
?                                          ----------------------

+  'S2': ['positive', 'negative', ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `guidecache/origin.py` → `GuidelineOrigin.fetch`: `published_at <= now` is the README rule ('at or before now'), so bbox en v2 (published 09:30) is correctly invisible during the trace while ner v2 (09:08) appears at N3. It returns a new dict with a copied label list, so callers can't mutate origin records.
