# set-028 answer key: Async embedding backfill: cache, retries, paginated usage

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** multi-bug. Tests can fail for several bugs at once, and some bugs stay hidden until others are fixed.

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_backoff_delays`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_1_requests.TestRequests.test_requests_per_model`
- `tests.test_2_documents.TestDocuments.test_embed_l`
- `tests.test_2_documents.TestDocuments.test_embed_s`
- `tests.test_3_summary.TestSummary.test_billed_tokens`
- `tests.test_3_summary.TestSummary.test_document_counts`
- `tests.test_3_summary.TestSummary.test_usage_read_page_by_page`

## Bugs (recommended order)

### B1: Semaphore created but never acquired

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_limit: the server saw 5 requests in flight at once (expected at most 2).
- **Location:** `embedq/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** self.sem is built from max_concurrency but nothing acquires it, so gather fires every batch at once and the server sees more than 2 requests in flight.
- **Unblocks:** test_1 test_concurrency_limit.

Fix:

```diff
-        response = await send_with_retries(
-            lambda: request_json("POST", url, self.headers, payload), self.policy, self.sleep)
+        async with self.sem:
+            response = await send_with_retries(
+                lambda: request_json("POST", url, self.headers, payload), self.policy, self.sleep)
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 5 not less than or equal to 2
```

### B2: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** Test 1 test_backoff_delays: the recorded delays are [] (expected [0.1, 0.2, 1.0]). The retries still happen, and Python warns that a coroutine was never awaited.
- **Location:** `embedq/retry.py` → `send_with_retries`
- **Why it fails:** Calling an async function without `await` only creates a coroutine object. It never runs (Python warns 'coroutine was never awaited'), so there is no wait between retries and the recorded delays are empty.
- **Unblocks:** test_1 test_backoff_delays.

Fix:

```diff
-            sleep(wait_time(response, policy, attempt))
+            await sleep(wait_time(response, policy, attempt))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_backoff_delays`):

```
AssertionError: Lists differ: [] != [0.1, 0.2, 1.0]

Second list contains 3 additional elements.
First extra element 0:
0.1

- []
+ [0.1, 0.2, 1.0]
```

### B3: Cache key ignores the model

- **Type:** cache-key-missing-param
- **Symptom:** Test 1: embed-l made 1 request instead of 7, and the delays are only [1.0]. Test 2 test_embed_l: every doc is ok, mostly with dims 4 (embed-s vectors). Test 3: embed-l counts (15, 0), billed tokens 27, only 2 usage pages.
- **Location:** `embedq/cache.py` → `VectorCache.key`
- **Why it fails:** With the key hashed from text only, every text embed-s already embedded counts as cached for embed-l. embed-l only sends the three texts embed-s failed on and reuses 4-dim embed-s vectors for everything else.
- **Unblocks:** test_1 request counts, test_2 embed-l rows, test_3 counts and tokens. It also exposes B4.

Fix:

```diff
-        return hashlib.sha1(text.encode()).hexdigest()
+        return hashlib.sha1(f"{model}\n{text}".encode()).hexdigest()
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_backoff_delays`):

```
AssertionError: Lists differ: [1.0] != [0.1, 0.2, 1.0]

First differing element 0:
1.0
0.1

Second list contains 2 additional elements.
First extra element 1:
0.2

- [1.0]
+ [0.1, 0.2, 1.0]
```

### B4: One retry too few

- **Type:** retry-off-by-one
- **Symptom:** Only visible after B3 is fixed. Test 1: embed-l made 6 requests (expected 7). Test 2: d05/d07/d08 embed-l fail with 503 'transient'. Test 3: embed-l counts (7, 8), billed tokens 71, 2 usage pages. The backoff delays are unchanged.
- **Location:** `embedq/retry.py` → `send_with_retries`
- **Why it fails:** range(max_retries) allows max_retries attempts in total, not max_retries retries. The warranty batch needs a third attempt on embed-l, so it ends on 503. The backoff list doesn't change, because the loop still sleeps after the second failure.
- **Unblocks:** embed-l docs d05/d07/d08, the embed-l counts and tokens, and the third usage page.
- **Masked:** invisible until B3 is fixed (identical test output either way).

Fix:

```diff
-    for attempt in range(policy.max_retries):
+    for attempt in range(policy.max_retries + 1):
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_requests_per_model`):

```
AssertionError: {'embed-s': 6, 'embed-l': 6} != {'embed-s': 6, 'embed-l': 7}
- {'embed-l': 6, 'embed-s': 6}
?             ^

+ {'embed-l': 7, 'embed-s': 6}
?             ^
```

### B5: Final 4xx treated as a success

- **Type:** ignoring-http-status
- **Symptom:** Test 2 test_embed_s: d09/d11/d12 show http_status None, reason 'invalid_response' (expected 400 / 'rejected'). The counts in Test 3 are unchanged.
- **Location:** `embedq/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** Only statuses that are still transient after retries raise EmbeddingError. A 400 'input too long' falls through to parse_vectors, which fails on the error body, so the batch is reported as invalid_response with no http_status.
- **Unblocks:** test_2 test_embed_s.

Fix:

```diff
-        if response.status in RETRYABLE:
+        if response.status != 200:
             raise EmbeddingError(response.status)
```

Observed with only this bug applied (`tests.test_2_documents.TestDocuments.test_embed_s`):

```
AssertionError: {'d01[286 chars]us': None, 'reason': 'invalid_response'}, 'd10[330 chars]: 4}} != {'d01[286 chars]us': 400, 'reason': 'rejected'}, 'd10': {'stat[303 chars]: 4}}
  {'d01': {'dims': 4, 'status': 'ok'},
   'd02': {'dims': 4, 'status': 'ok'},
   'd03': {'dims': 4, 'status': 'ok'},
   'd04': {'dims': 4, 'status': 'ok'},
   'd05': {'dims': 4, 'status': 'ok'},
   'd07': {'dims': 4, 'statu ...
```

### B6: Short usage page treated as the last

- **Type:** pagination-cursor
- **Symptom:** Test 3 only: billed tokens {'embed-s': 0, 'embed-l': 63} (expected 63/90), and only 1 usage page was requested (expected 3).
- **Location:** `embedq/usage.py` → `collect_usage`
- **Why it fails:** The server caps pages at 4 records even though page_size is 5, so the first page is always short. Stopping on a short page drops every later page: the embed-s records are never read.
- **Unblocks:** test_3 tokens and page count.
- **Masked:** only surfaces in test_3_summary.

Fix:

```diff
-        if cursor is None or len(page["data"]) < client.config.page_size:
+        if cursor is None:
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_billed_tokens`):

```
AssertionError: {'embed-s': 0, 'embed-l': 63} != {'embed-s': 63, 'embed-l': 90}
- {'embed-l': 63, 'embed-s': 0}
?             ^^             ^

+ {'embed-l': 90, 'embed-s': 63}
?             ^^             ^^
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `embedq/retry.py` → `wait_time`: `2 ** attempt` with attempt starting at 0 gives backoff, 2×backoff, ... exactly as rule 3 says, and Retry-After takes priority when present.
- `embedq/transport.py` → `request_json`: It runs the blocking urllib call in a worker thread via asyncio.to_thread and awaits it, which is what lets batches overlap. HTTP error statuses come back as Response objects, not exceptions.
