# set-036 answer key: Async embedding indexer: concurrency, retries, upserts

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_concurrency_limit` | B1 Fresh semaphore per batch |
| `test_1_requests.TestRequests.test_attempts_per_batch` | B2 One attempt short of max_retries + 1 |
| `test_1_requests.TestRequests.test_backoff_waits` | B3 Backoff sleep never awaited |
| `test_2_results.TestResults.test_index_results` | B4 Rejected upserts counted as stored |
| `test_3_report.TestReport.test_tokens_per_doc` | B5 Average tokens floored |
| `test_3_report.TestReport.test_near_duplicates` | B6 Similarity rounded before the threshold check |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_attempts_per_batch`
- `tests.test_1_requests.TestRequests.test_backoff_waits`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_2_results.TestResults.test_index_results`
- `tests.test_3_report.TestReport.test_near_duplicates`
- `tests.test_3_report.TestReport.test_tokens_per_doc`

## Bugs (recommended order)

### B1: Fresh semaphore per batch

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_limit: AssertionError 5 not less than or equal to 2. The server saw all five embedding batches in flight at once.
- **Location:** `vecsync/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** Each call builds its own Semaphore(2), so every batch acquires a semaphore nobody else shares. All five batches hit the server at once. The shared self.limit created in __init__ is what bounds concurrency across calls.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** Test 1 test_concurrency_limit.

Fix:

```diff
-        async with asyncio.Semaphore(self.config.max_concurrency):
+        async with self.limit:
             response = await send_with_retries(
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 5 not less than or equal to 2
```

### B2: One attempt short of max_retries + 1

- **Type:** retry-off-by-one
- **Symptom:** Test 1 test_attempts_per_batch: batch 2 was tried 3 times instead of 4 ({0: 1, 1: 2, 2: 3, ...}). Its result is still a 503 failure, so nothing else changes.
- **Location:** `vecsync/retry.py` → `send_with_retries`
- **Why it fails:** max_retries counts retries, not attempts: one initial try plus 3 retries is 4 requests. The batch fails either way (it always gets 503), so only the attempt count shows it. The loop still sleeps after its last attempt, which is why the recorded waits look the same.
- **Failing test:** `test_1_requests.TestRequests.test_attempts_per_batch`
- **Unblocks:** Test 1 test_attempts_per_batch.

Fix:

```diff
-    for attempt in range(policy.max_retries):
+    for attempt in range(policy.max_retries + 1):
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_attempts_per_batch`):

```
AssertionError: {0: 1, 1: 2, 2: 3, 3: 1, 4: 2} != {0: 1, 1: 2, 2: 4, 3: 1, 4: 2}
- {0: 1, 1: 2, 2: 3, 3: 1, 4: 2}
?                 ^

+ {0: 1, 1: 2, 2: 4, 3: 1, 4: 2}
?                 ^
```

### B3: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** Test 1 test_backoff_waits: the recorded waits are [] instead of [0.5, 0.5, 1.0, 2.0, 2.0], and the run prints RuntimeWarning: coroutine ... was never awaited. Retries still happen (attempt counts are right).
- **Location:** `vecsync/retry.py` → `send_with_retries`
- **Why it fails:** Calling an async function without await only creates a coroutine object; its body never runs, so no delay happens (and the test's recorder never sees it). Python prints a 'coroutine was never awaited' RuntimeWarning.
- **Failing test:** `test_1_requests.TestRequests.test_backoff_waits`
- **Unblocks:** Test 1 test_backoff_waits.

Fix:

```diff
-            sleep(wait_time(response, policy, attempt))
+            await sleep(wait_time(response, policy, attempt))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_backoff_waits`):

```
AssertionError: Lists differ: [] != [0.5, 0.5, 1.0, 2.0, 2.0]

Second list contains 5 additional elements.
First extra element 0:
0.5

- []
+ [0.5, 0.5, 1.0, 2.0, 2.0]
```

### B4: Rejected upserts counted as stored

- **Type:** gather-hides-failures
- **Symptom:** Test 2 test_index_results: {"stored": 14, "rejected": []} instead of {"stored": 13, "rejected": ["d07"]}, although the server answered d07 with 409.
- **Location:** `vecsync/pipeline.py` → `index_vectors`
- **Why it fails:** With return_exceptions=True, gather puts the UpsertError object into the results list instead of raising it. A failed upsert is never None, so the exception is stored as if it were a version number and d07's 409 disappears.
- **Failing test:** `test_2_results.TestResults.test_index_results`
- **Unblocks:** Test 2 test_index_results.

Fix:

```diff
-        if result is None:
+        if isinstance(result, Exception):
             run.rejected.append(doc_id)
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_index_results`):

```
AssertionError: {'stored': 14, 'rejected': []} != {'stored': 13, 'rejected': ['d07']}
- {'rejected': [], 'stored': 14}
?                             ^

+ {'rejected': ['d07'], 'stored': 13}
?               +++++              ^
```

### B5: Average tokens floored

- **Type:** integer-division
- **Symptom:** Test 3 test_tokens_per_doc: 14 != 14.86.
- **Location:** `vecsync/reports.py` → `summarize`
- **Why it fails:** // is floor division, so 208 tokens over 14 documents gives 14 instead of 14.857, and the 2-decimal rounding is lost too.
- **Failing test:** `test_3_report.TestReport.test_tokens_per_doc`
- **Unblocks:** Test 3 test_tokens_per_doc.

Fix:

```diff
-        "tokens_per_doc": run.total_tokens // embedded if embedded else None,
+        "tokens_per_doc": round(run.total_tokens / embedded, 2) if embedded else None,
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_tokens_per_doc`):

```
AssertionError: 14 != 14.86
```

### B6: Similarity rounded before the threshold check

- **Type:** float-rounding
- **Symptom:** Test 3 test_near_duplicates: an extra pair ["d15", "d16", 0.95] appears; its real similarity is 0.9477, below the 0.95 threshold.
- **Location:** `vecsync/similarity.py` → `near_duplicates`
- **Why it fails:** d15/d16 have cosine 0.9477. Rounded to 2 decimals that becomes 0.95, which passes the >= 0.95 threshold. The README compares the unrounded value and only rounds the reported number (to 3 decimals).
- **Failing test:** `test_3_report.TestReport.test_near_duplicates`
- **Unblocks:** Test 3 test_near_duplicates.

Fix:

```diff
-        sim = round(cosine(vectors[a], vectors[b]), 2)
+        sim = cosine(vectors[a], vectors[b])
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_near_duplicates`):

```
AssertionError: Lists differ: [['d03', 'd13', 1.0], ['d05', 'd14', 0.98], ['d15', 'd16', 0.95]] != [['d03', 'd13', 1.0], ['d05', 'd14', 0.98]]

First list contains 1 additional elements.
First extra element 2:
['d15', 'd16', 0.95]

- [['d03', 'd13', 1.0], ['d05', 'd14', 0.98], ['d15', 'd16', 0.95]]
?                                           --------------------- -

+ [['d03', 'd13', 1.0], ['d05', ...
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `vecsync/loader.py` → `batched`: range(0, len(items), size) steps through every start index and items[i:i + size] clamps at the end of the list, so the last short batch (d17, d18) is kept and nothing is duplicated.
- `vecsync/retry.py` → `wait_time`: Retry-After wins when present; otherwise backoff * 2 ** attempt. ** binds tighter than *, so this is backoff * (2 ** attempt): 0.5, 1.0, 2.0 for attempts 0, 1, 2, exactly as the README says.
