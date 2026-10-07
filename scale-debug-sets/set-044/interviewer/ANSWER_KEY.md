# set-044 answer key: Async embeddings batcher with bounded concurrency and index listing

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_concurrency_limit` | B1 Fresh semaphore created per batch |
| `test_1_requests.TestRequests.test_retry_after_honoured` | B2 Backoff sleep never awaited |
| `test_1_requests.TestRequests.test_attempts_per_batch` | B3 One retry too many |
| `test_2_results.TestResults.test_failed_batches` | B4 Exceptions from gather silently skipped |
| `test_3_summary.TestSummary.test_total_tokens` | B5 Token total snapshotted before the await |
| `test_3_summary.TestSummary.test_stale_ids` | B6 Last index page dropped |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_attempts_per_batch`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_1_requests.TestRequests.test_retry_after_honoured`
- `tests.test_2_results.TestResults.test_failed_batches`
- `tests.test_3_summary.TestSummary.test_stale_ids`
- `tests.test_3_summary.TestSummary.test_total_tokens`

## Bugs (recommended order)

### B1: Fresh semaphore created per batch

- **Type:** semaphore-unused
- **Symptom:** test_1 test_concurrency_limit: 'AssertionError: 7 not less than or equal to 2'. The server saw all 7 batches in flight at once, and every result is still correct.
- **Location:** `embedclient/client.py` → `EmbeddingClient._run_batch`
- **Why it fails:** Each call builds its own Semaphore, so every batch acquires a different, uncontended semaphore and nothing is limited. All seven batches hit the server at once. The shared `self._sem` created in __init__ is never used.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** test_concurrency_limit

Fix:

```diff
-        async with asyncio.Semaphore(self.config.max_concurrency):
+        async with self._sem:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 7 not less than or equal to 2
```

### B2: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** test_1 test_retry_after_honoured: b2's retry arrives about 0.06 s after the first attempt instead of at least 0.2 s. The output also shows a RuntimeWarning that coroutine 'sleep' was never awaited.
- **Location:** `embedclient/retry.py` → `post_with_retries`
- **Why it fails:** Calling asyncio.sleep() without await only creates a coroutine object, which is thrown away (Python warns 'coroutine ... was never awaited'). The retry goes out right away instead of after the 0.2 s Retry-After.
- **Failing test:** `test_1_requests.TestRequests.test_retry_after_honoured`
- **Unblocks:** test_retry_after_honoured

Fix:

```diff
-        asyncio.sleep(backoff_delay(resp, attempt, backoff_seconds))
+        await asyncio.sleep(backoff_delay(resp, attempt, backoff_seconds))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_retry_after_honoured`):

```
AssertionError: 0.057725457998458296 not greater than or equal to 0.2
```

### B3: One retry too many

- **Type:** retry-off-by-one
- **Symptom:** test_1 test_attempts_per_batch: b4 was attempted 4 times instead of 3. Everything else matches, and b4 is still reported as HTTP 503.
- **Location:** `embedclient/retry.py` → `post_with_retries`
- **Why it fails:** `attempt` counts retries already made, starting at 0. With `>` the loop returns only after max_retries + 1 retries, so b4 (always 503) is sent 4 times instead of max_retries + 1 = 3.
- **Failing test:** `test_1_requests.TestRequests.test_attempts_per_batch`
- **Unblocks:** test_attempts_per_batch

Fix:

```diff
-if resp.status not in TRANSIENT or attempt > max_retries:
+if resp.status not in TRANSIENT or attempt >= max_retries:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_attempts_per_batch`):

```
AssertionError: {'b1': 1, 'b2': 2, 'b3': 1, 'b4': 4, 'b5': 1, 'b6': 1, 'b7': 1} != {'b1': 1, 'b2': 2, 'b3': 1, 'b4': 3, 'b5': 1, 'b6': 1, 'b7': 1}
- {'b1': 1, 'b2': 2, 'b3': 1, 'b4': 4, 'b5': 1, 'b6': 1, 'b7': 1}
?                                   ^

+ {'b1': 1, 'b2': 2, 'b3': 1, 'b4': 3, 'b5': 1, 'b6': 1, 'b7': 1}
?                                   ^
```

### B4: Exceptions from gather silently skipped

- **Type:** gather-hides-failures
- **Symptom:** test_2 test_failed_batches: `failed` is {} instead of {'b4': 'HTTP 503', 'b6': 'HTTP 400'}. Vectors and missing_docs are still right.
- **Location:** `embedclient/client.py` → `EmbeddingClient.embed_all`
- **Why it fails:** gather(..., return_exceptions=True) returns the BatchFailed exceptions as values. The loop skips them without recording them, so `failed` is always empty and the failed batches simply disappear.
- **Failing test:** `test_2_results.TestResults.test_failed_batches`
- **Unblocks:** test_failed_batches

Fix:

```diff
             if isinstance(result, Exception):
+                failed[batch.id] = str(result)
                 continue
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_failed_batches`):

```
AssertionError: {} != {'b4': 'HTTP 503', 'b6': 'HTTP 400'}
- {}
+ {'b4': 'HTTP 503', 'b6': 'HTTP 400'}
```

### B5: Token total snapshotted before the await

- **Type:** async-shared-state
- **Symptom:** test_3 test_total_tokens: a lower total (71 in the verification run; the exact value depends on how the batches overlap) instead of 91.
- **Location:** `embedclient/client.py` → `EmbeddingClient._embed_batch`
- **Why it fails:** The shared counter is read before the request and written after it. Another batch updates it while this one is awaiting, and the write then overwrites that update, so tokens are lost.
- **Failing test:** `test_3_summary.TestSummary.test_total_tokens`
- **Unblocks:** test_total_tokens

Fix:

```diff
-        tokens_before = self.usage_tokens
         resp = await post_with_retries(f"{self.base_url}/v1/embeddings", self.headers, payload,
                                        self.config.max_retries, self.config.backoff_seconds)
             raise BatchFailed(f"HTTP {resp.status}")
         body = resp.body
-        self.usage_tokens = tokens_before + body["usage"]["total_tokens"]
+        self.usage_tokens += body["usage"]["total_tokens"]
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_total_tokens`):

```
AssertionError: 25 != 91
```

### B6: Last index page dropped

- **Type:** pagination-cursor
- **Symptom:** test_3 test_stale_ids: ['d31'] instead of ['d27', 'd31', 'd40']. Three index pages are still requested.
- **Location:** `embedclient/index.py` → `list_index_ids`
- **Why it fails:** The loop breaks on a null cursor before keeping the page it just fetched, so the last page (d40, d27) is fetched but never added. All three pages are still requested, which hides the problem.
- **Failing test:** `test_3_summary.TestSummary.test_stale_ids`
- **Unblocks:** test_stale_ids

Fix:

```diff
+        ids.extend(resp.body["ids"])
         cursor = resp.body.get("next_cursor")
         if not cursor:
             break
-        ids.extend(resp.body["ids"])
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_stale_ids`):

```
AssertionError: Lists differ: ['d31'] != ['d27', 'd31', 'd40']

First differing element 0:
'd31'
'd27'

Second list contains 2 additional elements.
First extra element 1:
'd31'

- ['d31']
+ ['d27', 'd31', 'd40']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `embedclient/retry.py` → `backoff_delay`: It returns Retry-After as a float when present (the spec allows fractional values), else base × 2^attempt with attempt starting at 0, so the first fallback wait is exactly backoff_seconds. `2 ** attempt` binds tighter than `*`, so the expression is base * (2 ** attempt).
