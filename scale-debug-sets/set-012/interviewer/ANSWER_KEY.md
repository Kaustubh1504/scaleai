# set-012 answer key: Async embeddings batch sync with usage pagination

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_1_attempts_per_batch` | B1 One retry too few |
| `test_1_requests.TestRequests.test_2_retry_after_honoured` | B2 Backoff sleep never awaited |
| `test_1_requests.TestRequests.test_3_concurrency_limit` | B3 Semaphore created but never acquired |
| `test_2_results.TestResults.test_4_failed_documents` | B4 ValueError handler shadows JSONDecodeError |
| `test_3_report.TestReport.test_5_total_tokens` | B5 Usage cursor taken from the first record of the page |
| `test_3_report.TestReport.test_6_near_duplicates` | B6 Near-duplicates listed least similar first |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_1_attempts_per_batch`
- `tests.test_1_requests.TestRequests.test_2_retry_after_honoured`
- `tests.test_1_requests.TestRequests.test_3_concurrency_limit`
- `tests.test_2_results.TestResults.test_4_failed_documents`
- `tests.test_3_report.TestReport.test_5_total_tokens`
- `tests.test_3_report.TestReport.test_6_near_duplicates`

## Bugs (recommended order)

### B1: One retry too few

- **Type:** retry-off-by-one
- **Symptom:** test_1_attempts_per_batch fails: b04 (always 503) gets 2 attempts instead of 3. Every other batch matches.
- **Location:** `vecbatch/retry.py` → `send_with_retries`
- **Why it fails:** max_retries is the number of retries, so the total allowed is max_retries + 1 attempts. `>=` stops after max_retries attempts in total.
- **Failing test:** `test_1_requests.TestRequests.test_1_attempts_per_batch`
- **Unblocks:** test_1_attempts_per_batch.

Fix:

```diff
-or attempts >= max_retries:
+or attempts > max_retries:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_1_attempts_per_batch`):

```
AssertionError: {'b01': 1, 'b02': 2, 'b03': 2, 'b04': 2, 'b05': 1, 'b06': 1, 'b07': 1, 'b08': 1} != {'b01': 1, 'b02': 2, 'b03': 2, 'b04': 3, 'b05': 1, 'b06': 1, 'b07': 1, 'b08': 1}
- {'b01': 1, 'b02': 2, 'b03': 2, 'b04': 2, 'b05': 1, 'b06': 1, 'b07': 1, 'b08': 1}
?                                       ^

+ {'b01': 1, 'b02': 2, 'b03': 2, 'b04': 3, 'b05': 1, 'b06': 1, 'b07': 1, 'b08': 1}
?          ...
```

### B2: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** test_2_retry_after_honoured fails: b02's second attempt arrives about 0.33 s after the first, although the 429 carried Retry-After: 1 (the 0.33 s is only time spent queued behind other batches). A 'coroutine ... was never awaited' RuntimeWarning appears.
- **Location:** `vecbatch/retry.py` → `send_with_retries`
- **Why it fails:** Calling asyncio.sleep() without await only creates a coroutine object, which is thrown away. Nothing waits, so the retry goes out immediately and ignores Retry-After (Python also prints 'coroutine ... was never awaited').
- **Failing test:** `test_1_requests.TestRequests.test_2_retry_after_honoured`
- **Unblocks:** test_2_retry_after_honoured.

Fix:

```diff
-        asyncio.sleep(retry_delay(response, attempts - 1, backoff_seconds))
+        await asyncio.sleep(retry_delay(response, attempts - 1, backoff_seconds))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_2_retry_after_honoured`):

```
AssertionError: 0.34 not greater than or equal to 1.0
```

### B3: Semaphore created but never acquired

- **Type:** semaphore-unused
- **Symptom:** test_3_concurrency_limit fails: the server saw 8 requests in flight at once instead of at most 2.
- **Location:** `vecbatch/client.py` → `EmbeddingClient._post`
- **Why it fails:** The semaphore is built in __init__ with max_concurrency, but no request acquires it, so gather() starts every batch at once.
- **Failing test:** `test_1_requests.TestRequests.test_3_concurrency_limit`
- **Unblocks:** test_3_concurrency_limit.

Fix:

```diff
-        return await request(
+        async with self.semaphore:
+            return await request(
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_3_concurrency_limit`):

```
AssertionError: 8 != 2
```

### B4: ValueError handler shadows JSONDecodeError

- **Type:** exception-order
- **Symptom:** test_4_failed_documents fails: d09 and d10 (batch b05, whose body is cut-off JSON) are reported as 'invalid' instead of 'bad_json'.
- **Location:** `vecbatch/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** json.JSONDecodeError is a subclass of ValueError. except clauses are tried top to bottom, so the ValueError handler catches the decode error first and the bad_json branch can never run.
- **Failing test:** `test_2_results.TestResults.test_4_failed_documents`
- **Unblocks:** test_4_failed_documents.

Fix:

```diff
+        except json.JSONDecodeError:
+            return BatchResult(batch.batch_id, "bad_json", attempts, http_status=response.status)
         except ValueError:
             return BatchResult(batch.batch_id, "invalid", attempts, http_status=response.status)
-        except json.JSONDecodeError:
-            return BatchResult(batch.batch_id, "bad_json", attempts, http_status=response.status)
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_4_failed_documents`):

```
AssertionError: {'d07[41 chars]9': 'invalid', 'd10': 'invalid', 'd13': 'inval[17 chars]lid'} != {'d07[41 chars]9': 'bad_json', 'd10': 'bad_json', 'd13': 'inv[19 chars]lid'}
  {'d07': 'http_error',
   'd08': 'http_error',
-  'd09': 'invalid',
-  'd10': 'invalid',
+  'd09': 'bad_json',
+  'd10': 'bad_json',
   'd13': 'invalid',
   'd14': 'invalid'}
```

### B5: Usage cursor taken from the first record of the page

- **Type:** pagination-cursor
- **Symptom:** test_5_total_tokens fails: total_tokens is 252 instead of 121, because overlapping usage pages are counted again.
- **Location:** `vecbatch/pipeline.py` → `collect_usage`
- **Why it fails:** `after=first_id` asks for everything after the first record of the page just read, so the next page repeats all but one of its records. Pages overlap and tokens are counted several times.
- **Failing test:** `test_3_report.TestReport.test_5_total_tokens`
- **Unblocks:** test_5_total_tokens.

Fix:

```diff
-        after = page["first_id"]
+        after = page["last_id"]
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_5_total_tokens`):

```
AssertionError: 251 != 121
```

### B6: Near-duplicates listed least similar first

- **Type:** sort-direction
- **Symptom:** test_6_near_duplicates fails: the three pairs come back in reverse order, [d02,d11,0.945] first and [d03,d12,1.0] last.
- **Location:** `vecbatch/similarity.py` → `near_duplicates`
- **Why it fails:** The sort key uses the similarity ascending, but the spec wants the most similar pair first. The docstring still says most similar first.
- **Failing test:** `test_3_report.TestReport.test_6_near_duplicates`
- **Unblocks:** test_6_near_duplicates.

Fix:

```diff
-key=lambda p: (p[2], p[0], p[1]))
+key=lambda p: (-p[2], p[0], p[1]))
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_6_near_duplicates`):

```
AssertionError: Lists differ: [['d02', 'd11', 0.945], ['d01', 'd05', 0.956], ['d03', 'd12', 1.0]] != [['d03', 'd12', 1.0], ['d01', 'd05', 0.956], ['d02', 'd11', 0.945]]

First differing element 0:
['d02', 'd11', 0.945]
['d03', 'd12', 1.0]

- [['d02', 'd11', 0.945], ['d01', 'd05', 0.956], ['d03', 'd12', 1.0]]
+ [['d03', 'd12', 1.0], ['d01', 'd05', 0.956], ['d02', 'd11', 0.945]]
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `vecbatch/transport.py` → `_send`: HTTPError is caught and turned into a normal Response with the real status and headers, so 4xx/5xx reach the retry logic instead of raising. Network errors (URLError) are deliberately left to propagate.
- `vecbatch/pipeline.py` → `make_batches`: `range(0, len(docs), size)` with `docs[start:start + size]` covers every document exactly once and allows a short final batch; `enumerate(..., start=1)` gives b01, b02, ... as the spec requires.
