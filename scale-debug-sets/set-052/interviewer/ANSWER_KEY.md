# set-052 answer key: Async embedding indexer: concurrency cap, retries, paginated usage

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_concurrency_limit` | B1 Fresh semaphore per request |
| `test_1_requests.TestRequests.test_backoff_waits` | B2 Backoff sleep never awaited |
| `test_2_batches.TestBatches.test_batch_outcomes` | B3 Only 5xx treated as failure |
| `test_2_batches.TestBatches.test_vectors` | B4 Collection options merged into shared defaults |
| `test_3_report.TestReport.test_total_tokens` | B5 First usage page dropped |
| `test_3_report.TestReport.test_by_collection` | B6 Shared default dict in tally |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_backoff_waits`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_2_batches.TestBatches.test_batch_outcomes`
- `tests.test_2_batches.TestBatches.test_vectors`
- `tests.test_3_report.TestReport.test_by_collection`
- `tests.test_3_report.TestReport.test_total_tokens`

## Bugs (recommended order)

### B1: Fresh semaphore per request

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_limit: `7 not less than or equal to 2`. The server saw all seven batches in flight at once.
- **Location:** `embedindex/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** Each call creates its own semaphore and is the only task that ever acquires it, so nothing is limited. The shared `self.limit` built in __init__ is never used.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** test_concurrency_limit.

Fix:

```diff
-        async with asyncio.Semaphore(self.config.max_concurrency):
+        async with self.limit:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 7 not less than or equal to 2
```

### B2: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** Test 1 test_backoff_waits: the recorded waits are [] instead of [0.01, 0.05, 0.05, 0.1, 0.1]. Retries still happen (attempt counts are right), and Python warns 'coroutine ... was never awaited'.
- **Location:** `embedindex/retry.py` → `send_with_retries`
- **Why it fails:** Calling an async function without await only creates a coroutine object; it never runs. So retries go out immediately and the recorded waits are empty (Python prints 'coroutine was never awaited').
- **Failing test:** `test_1_requests.TestRequests.test_backoff_waits`
- **Unblocks:** test_backoff_waits.

Fix:

```diff
-        sleep(wait_time(response, policy, attempt))
+        await sleep(wait_time(response, policy, attempt))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_backoff_waits`):

```
AssertionError: Lists differ: [] != [0.01, 0.05, 0.05, 0.1, 0.1]

Second list contains 5 additional elements.
First extra element 0:
0.01

- []
+ [0.01, 0.05, 0.05, 0.1, 0.1]
```

### B3: Only 5xx treated as failure

- **Type:** ignoring-http-status
- **Symptom:** Test 2 test_batch_outcomes: kb-02 shows ('ok', 422, 1) instead of ('failed', 422, 1).
- **Location:** `embedindex/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** The README says any final status other than 200 fails the batch. The 422 validation error is below 500, so it falls through to parsing; the error body has no `data`, so the batch is reported ok with zero vectors.
- **Failing test:** `test_2_batches.TestBatches.test_batch_outcomes`
- **Unblocks:** test_batch_outcomes.

Fix:

```diff
-        if response.status >= 500:
+        if response.status != 200:
             result.status = "failed"
```

Observed with only this bug applied (`tests.test_2_batches.TestBatches.test_batch_outcomes`):

```
AssertionError: {'faq[105 chars]': ('ok', 422, 1), 'policies-01': ('failed', 5[33 chars], 1)} != {'faq[105 chars]': ('failed', 422, 1), 'policies-01': ('failed[37 chars], 1)}
  {'faq-01': ('ok', 200, 1),
   'faq-02': ('ok', 200, 2),
   'faq-03': ('ok', 200, 1),
   'kb-01': ('ok', 200, 3),
-  'kb-02': ('ok', 422, 1),
?             ^^

+  'kb-02': ('failed', 422, 1),
?             ^^^^^^

   'polici ...
```

### B4: Collection options merged into shared defaults

- **Type:** async-shared-state
- **Symptom:** Test 2 test_vectors: the kb vectors come back unit-length (k01 is [0.4838, 0.1478, 0.0672, 0.86] instead of the raw [36.0, 11.0, 5.0, 64.0]). faq and policies vectors are unchanged.
- **Location:** `embedindex/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** Every task updates the same `self.defaults` dict before its first await. By the time any response comes back, the dict holds the last-started batch's options (policies: normalize true), so kb vectors are normalised although kb says normalize false.
- **Failing test:** `test_2_batches.TestBatches.test_vectors`
- **Unblocks:** test_vectors.

Fix:

```diff
-        options = self.defaults
+        options = dict(self.defaults)
```

Observed with only this bug applied (`tests.test_2_batches.TestBatches.test_vectors`):

```
AssertionError: {'f01[321 chars]1': [0.4838, 0.1478, 0.0672, 0.86], 'k02': [0.[104 chars]388]} != {'f01[321 chars]1': [36.0, 11.0, 5.0, 64.0], 'k02': [34.0, 12.[82 chars]388]}
  {'f01': [0.5149, 0.1335, 0.1144, 0.839],
   'f02': [0.5251, 0.175, 0.0955, 0.8274],
   'f03': [0.478, 0.1487, 0.0956, 0.8604],
   'f04': [0.5597, 0.1544, 0.0772, 0.8105],
   'f06': [0.6356, 0.2311, 0.1445, 0.7223],
   'f07 ...
```

### B5: First usage page dropped

- **Type:** pagination-cursor
- **Symptom:** Test 3 test_total_tokens: a total such as 31 instead of 63. The exact shortfall depends on which batches finished first, since those records sit on the first page.
- **Location:** `embedindex/indexer.py` → `fetch_usage`
- **Why it fails:** The first page is fetched before the loop, but its records are thrown away; only the pages reached by following next_cursor are kept.
- **Failing test:** `test_3_report.TestReport.test_total_tokens`
- **Unblocks:** test_total_tokens.

Fix:

```diff
-    records = []
+    records = list(page["data"])
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_total_tokens`):

```
AssertionError: 31 != 63
```

### B6: Shared default dict in tally

- **Type:** mutable-default
- **Symptom:** Test 3 test_by_collection: every collection shows the same dict, e.g. {'docs': 54, 'embedded': 36} in a full-suite run. The numbers keep growing with each build_report call in the process, so running test_3 alone gives {'docs': 18, 'embedded': 12} for every collection.
- **Location:** `embedindex/reports.py` → `tally`
- **Why it fails:** A default `{}` is created once when the function is defined, so every call that doesn't pass counts adds into the same dict. Every collection ends up pointing at one dict holding the running total.
- **Failing test:** `test_3_report.TestReport.test_by_collection`
- **Unblocks:** test_by_collection.

Fix:

```diff
-def tally(results, counts={}):
+def tally(results, counts=None):
+    counts = {} if counts is None else counts
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_by_collection`):

```
AssertionError: {'faq': {'docs': 54, 'embedded': 36}, 'kb': {'docs': 54, '[52 chars] 36}} != {'faq': {'docs': 8, 'embedded': 8}, 'kb': {'docs': 6, 'emb[46 chars]: 1}}
- {'faq': {'docs': 54, 'embedded': 36},
?                  ^^              ^^

+ {'faq': {'docs': 8, 'embedded': 8},
?                  ^              ^

-  'kb': {'docs': 54, 'embedded': 36},
?                 ^^               -

+  ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `embedindex/retry.py` → `wait_time`: Retry-After wins when present, otherwise backoff × 2**attempt with attempt starting at 0, exactly as the README says. `2 ** attempt` without parentheses is fine because ** binds tighter than *.
- `embedindex/indexer.py` → `make_batches`: groupby is only safe on sorted input, and it is sorted by collection first. sorted() is stable, so documents keep their file order inside each collection, and numbering starts at 01 per collection.
