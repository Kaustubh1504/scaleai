# set-060 answer key: Async embedding backfill: paginated dataset, batches, index commit

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_dataset_fully_read` | B1 Last page's records dropped |
| `test_1_requests.TestRequests.test_concurrency_limit` | B2 Semaphore created but never acquired for embeddings |
| `test_1_requests.TestRequests.test_backoff_between_attempts` | B3 Backoff sleep never awaited |
| `test_2_results.TestResults.test_rejected_batch` | B4 4xx responses passed to the parser |
| `test_2_results.TestResults.test_dimension_mismatch` | B5 Base ResponseError caught before DimensionMismatch |
| `test_3_report.TestReport.test_commit_outcomes` | B6 One upsert failure hides every commit outcome |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_backoff_between_attempts`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_1_requests.TestRequests.test_dataset_fully_read`
- `tests.test_2_results.TestResults.test_dimension_mismatch`
- `tests.test_2_results.TestResults.test_rejected_batch`
- `tests.test_3_report.TestReport.test_commit_outcomes`

## Bugs (recommended order)

### B1: Last page's records dropped

- **Type:** pagination-cursor
- **Symptom:** test_1_requests.test_dataset_fully_read: (fetched, pages) is (25, 6) instead of (27, 6). Selection, batches and vectors are unchanged because the last page holds only deleted records.
- **Location:** `vecsync/dataset.py` → `fetch_all`
- **Why it fails:** The loop breaks as soon as next_page_token is null, before the page that carried the null token is added, so the final page's records (faq-26, faq-27) are lost. They happen to be deleted records, so nothing downstream changes, only `fetched`.
- **Failing test:** `test_1_requests.TestRequests.test_dataset_fully_read`
- **Unblocks:** test_dataset_fully_read.

Fix:

```diff
+        records.extend(page["records"])
         token = page.get("next_page_token")
         if not token:
             break
-        records.extend(page["records"])
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_dataset_fully_read`):

```
AssertionError: Tuples differ: (25, 6) != (27, 6)

First differing element 0:
25
27

- (25, 6)
?   ^

+ (27, 6)
?   ^
```

### B2: Semaphore created but never acquired for embeddings

- **Type:** semaphore-unused
- **Symptom:** test_1_requests.test_concurrency_limit: max_in_flight is 6 (or however many worker threads are free) instead of 2.
- **Location:** `vecsync/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** self.sem is built from max_concurrency but embed_batch never enters it, so gather launches all six batches at once and the server sees more than 2 embedding requests in flight.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** test_concurrency_limit.

Fix:

```diff
-        response, attempts = await self._send_embeddings(batch_id, records)
+        async with self.sem:
+            response, attempts = await self._send_embeddings(batch_id, records)
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 6 != 2
```

### B3: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** test_1_requests.test_backoff_between_attempts: 'gaps between b2 attempts: [0.059, 0.052]' (about the server latency) instead of at least 0.1 and 0.2 s. A 'coroutine ... was never awaited' RuntimeWarning appears in the output. Attempt counts stay right.
- **Location:** `vecsync/retry.py` → `with_retries`
- **Why it fails:** asyncio.sleep() only creates a coroutine; without await it never runs (Python warns 'coroutine was never awaited'), so retries go out immediately with no backoff.
- **Failing test:** `test_1_requests.TestRequests.test_backoff_between_attempts`
- **Unblocks:** test_backoff_between_attempts.

Fix:

```diff
-        asyncio.sleep(backoff_delay(response, attempt, base))
+        await asyncio.sleep(backoff_delay(response, attempt, base))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_backoff_between_attempts`):

```
AssertionError: False is not true : gaps between b2 attempts: [0.063, 0.054]
```

### B4: 4xx responses passed to the parser

- **Type:** ignoring-http-status
- **Symptom:** test_2_results.test_rejected_batch: b5 has status 'bad_response' (http_status 400) instead of 'http_error'.
- **Location:** `vecsync/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** Only 5xx is treated as an HTTP failure, so b5's 400 error body is handed to parse_embeddings, which finds no data list and reports bad_response, hiding the real HTTP status problem.
- **Failing test:** `test_2_results.TestResults.test_rejected_batch`
- **Unblocks:** test_rejected_batch.

Fix:

```diff
-        if response.status >= 500:
+        if response.status >= 400:
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_rejected_batch`):

```
AssertionError: {'status': 'bad_response', 'http_status': 400, 'attem[56 chars]23']} != {'status': 'http_error', 'http_status': 400, 'attempt[54 chars]23']}
  {'attempts': 1,
   'http_status': 400,
   'records': ['faq-20', 'faq-21', 'faq-22', 'faq-23'],
-  'status': 'bad_response'}
+  'status': 'http_error'}
```

### B5: Base ResponseError caught before DimensionMismatch

- **Type:** exception-order
- **Symptom:** test_2_results.test_dimension_mismatch: b4 has status 'bad_response' instead of 'dim_mismatch'.
- **Location:** `vecsync/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** DimensionMismatch subclasses ResponseError, and except clauses are tried top to bottom, so the base-class clause catches it first and the dim_mismatch branch can never run.
- **Failing test:** `test_2_results.TestResults.test_dimension_mismatch`
- **Unblocks:** test_dimension_mismatch.

Fix:

```diff
+        except DimensionMismatch:
+            result.status = "dim_mismatch"
         except ResponseError:
             result.status = "bad_response"
-        except DimensionMismatch:
-            result.status = "dim_mismatch"
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_dimension_mismatch`):

```
AssertionError: {'status': 'bad_response', 'http_status': 200, 'attem[56 chars]19']} != {'status': 'dim_mismatch', 'http_status': 200, 'attem[56 chars]19']}
  {'attempts': 1,
   'http_status': 200,
   'records': ['faq-16', 'faq-17', 'faq-18', 'faq-19'],
-  'status': 'bad_response'}
+  'status': 'dim_mismatch'}
```

### B6: One upsert failure hides every commit outcome

- **Type:** gather-hides-failures
- **Symptom:** test_3_report.test_commit_outcomes: {'committed': [], 'failed': ['b6']} instead of {'committed': ['b1', 'b2', 'b3'], 'failed': ['b6']}.
- **Location:** `vecsync/runner.py` → `commit`
- **Why it fails:** Without return_exceptions, gather raises b6's UpsertError as soon as it happens and the other outcomes are thrown away. run() catches it and reports committed [] / failed ['b6'], although b1-b3 committed fine.
- **Failing test:** `test_3_report.TestReport.test_commit_outcomes`
- **Unblocks:** test_commit_outcomes.

Fix:

```diff
-    outcomes = await asyncio.gather(*(client.upsert(r) for r in ok))
+    outcomes = await asyncio.gather(*(client.upsert(r) for r in ok), return_exceptions=True)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_commit_outcomes`):

```
AssertionError: {'committed': [], 'failed': ['b6']} != {'committed': ['b1', 'b2', 'b3'], 'failed': ['b6']}
- {'committed': [], 'failed': ['b6']}
+ {'committed': ['b1', 'b2', 'b3'], 'failed': ['b6']}
?                ++++++++++++++++
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `vecsync/retry.py` → `backoff_delay`: `2 ** (attempt - 1)` looks like an off-by-one next to the README's backoff_s x 2^(n-1), but attempt is 1-based here (with_retries increments before calling), so the first wait is backoff_s and the second is 2 x backoff_s, exactly as specified. Retry-After takes precedence, including '0'.
