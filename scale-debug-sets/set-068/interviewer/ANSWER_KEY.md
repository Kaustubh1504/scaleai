# set-068 answer key: Async embedding backfill: concurrency cap, retries, index matching

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** medium

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_request_body` | B1 datetime serialised with str() |
| `test_1_requests.TestRequests.test_concurrency_limit` | B2 Fresh semaphore per batch |
| `test_2_retries.TestRetries.test_attempts_per_batch` | B3 Retry loop one attempt short |
| `test_2_retries.TestRetries.test_retry_after_respected` | B4 Backoff sleep not awaited |
| `test_3_report.TestReport.test_doc_norms` | B5 Embeddings matched by position |
| `test_3_report.TestReport.test_summary` | B6 tokens_per_doc floor-divided |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_1_requests.TestRequests.test_request_body`
- `tests.test_2_retries.TestRetries.test_attempts_per_batch`
- `tests.test_2_retries.TestRetries.test_retry_after_respected`
- `tests.test_3_report.TestReport.test_doc_norms`
- `tests.test_3_report.TestReport.test_summary`

## Bugs (recommended order)

### B1: datetime serialised with str()

- **Type:** json-serialization
- **Symptom:** Test 1 test_request_body: metadata.newest_update is '2026-04-03 08:15:00' instead of '2026-04-03T08:15:00'. Everything else in the body matches.
- **Location:** `embedclient/payloads.py` → `_encode_value`
- **Why it fails:** str(datetime) uses a space between date and time ('2026-04-03 08:15:00'), not the ISO 8601 'T' form the README requires for newest_update.
- **Failing test:** `test_1_requests.TestRequests.test_request_body`
- **Unblocks:** test_request_body.

Fix:

```diff
-        return str(value)
+        return value.isoformat()
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_request_body`):

```
AssertionError: {'mod[185 chars], 'faq-02', 'faq-03'], 'newest_update': '2026-04-03 08:15:00'}} != {'mod[185 chars], 'faq-02', 'faq-03'], 'newest_update': '2026-04-03T08:15:00'}}
  {'input': ['How do I reset my password',
             'Where can I download my invoices',
             'Can I change the billing email'],
   'metadata': {'batch_id': 'b01',
                'doc_ids': ['faq-01', 'faq-02' ...
```

### B2: Fresh semaphore per batch

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_limit: '7 not less than or equal to 2'. The server saw all 7 batches in flight at once. All results are unchanged.
- **Location:** `embedclient/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** Each call builds its own semaphore, so every batch acquires a private one immediately. The shared self._limit is created but never used, and all 7 batches hit the server at once.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** test_concurrency_limit.

Fix:

```diff
-        async with asyncio.Semaphore(self.config.max_concurrency):
+        async with self._limit:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 7 not less than or equal to 2
```

### B3: Retry loop one attempt short

- **Type:** retry-off-by-one
- **Symptom:** Test 2 test_attempts_per_batch: b04 gets 2 attempts (server-side and reported) instead of 3. Its final status is still failed/503.
- **Location:** `embedclient/retry.py` → `send_with_retries`
- **Why it fails:** max_retries counts retries, so there are max_retries + 1 attempts. range(max_retries) stops after 2 attempts for b04, which always returns 503.
- **Failing test:** `test_2_retries.TestRetries.test_attempts_per_batch`
- **Unblocks:** test_attempts_per_batch.

Fix:

```diff
-    for attempt in range(max_retries):
+    for attempt in range(max_retries + 1):
```

Observed with only this bug applied (`tests.test_2_retries.TestRetries.test_attempts_per_batch`):

```
AssertionError: Tuples differ: ({'b0[29 chars]04': 2, 'b05': 1, 'b06': 2, 'b07': 1}, {'b01':[59 chars]: 1}) != ({'b0[29 chars]04': 3, 'b05': 1, 'b06': 2, 'b07': 1}, {'b01':[59 chars]: 1})

First differing element 0:
{'b01': 1, 'b02': 2, 'b03': 1, 'b04': 2, 'b05': 1, 'b06': 2, 'b07': 1}
{'b01': 1, 'b02': 2, 'b03': 1, 'b04': 3, 'b05': 1, 'b06': 2, 'b07': 1}

- ({'b01': 1, 'b02': 2, 'b03': 1, 'b04':  ...
```

### B4: Backoff sleep not awaited

- **Type:** missing-await
- **Symptom:** Test 2 test_retry_after_respected: the two b02 requests are about 0.09 s apart ('0.09 not greater than or equal to 0.3'). A 'coroutine ... was never awaited' RuntimeWarning is printed.
- **Location:** `embedclient/retry.py` → `send_with_retries`
- **Why it fails:** Calling asyncio.sleep() without await only creates a coroutine object, which is thrown away; nothing waits, so b02 is retried right after the 429 despite Retry-After: 0.3. Python logs 'coroutine ... was never awaited'.
- **Failing test:** `test_2_retries.TestRetries.test_retry_after_respected`
- **Unblocks:** test_retry_after_respected.

Fix:

```diff
-        asyncio.sleep(retry_delay(response, attempt, backoff_s))
+        await asyncio.sleep(retry_delay(response, attempt, backoff_s))
```

Observed with only this bug applied (`tests.test_2_retries.TestRetries.test_retry_after_respected`):

```
AssertionError: 0.08 not greater than or equal to 0.3
```

### B5: Embeddings matched by position

- **Type:** wrong-field
- **Symptom:** Test 3 test_doc_norms: sup-01 shows 10.77 and sup-04 shows 6.403 (swapped). sup-03 and every other document are correct.
- **Location:** `embedclient/client.py` → `EmbeddingClient._outcome`
- **Why it fails:** zip pairs documents with items by position, but the README says items can arrive in any order and must be matched by their `index` field. b03's items come back reversed, so sup-01 and sup-04 swap vectors.
- **Failing test:** `test_3_report.TestReport.test_doc_norms`
- **Unblocks:** test_doc_norms.

Fix:

```diff
-        for doc, item in zip(batch["docs"], response.body["data"]):
+        for item in response.body["data"]:
+            doc = batch["docs"][item["index"]]
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_doc_norms`):

```
AssertionError: {'faq[102 chars]01': 10.77, 'sup-03': 7.81, 'sup-04': 6.403, '[95 chars].708} != {'faq[102 chars]01': 6.403, 'sup-03': 7.81, 'sup-04': 10.77, '[95 chars].708}
  {'faq-01': 7.28,
   'faq-02': 10.05,
   'faq-03': 8.367,
   'faq-07': 8.124,
   'faq-08': 9.95,
   'faq-09': 6.708,
   'leg-01': 8.775,
   'leg-02': 7.483,
   'leg-03': 8.367,
-  'sup-01': 10.77,
?            ^ ^^^

+  'sup ...
```

### B6: tokens_per_doc floor-divided

- **Type:** integer-division
- **Symptom:** Test 3 test_summary: tokens_per_doc is 6 instead of 6.93. The other summary fields match.
- **Location:** `embedclient/reports.py` → `summarize`
- **Why it fails:** // is floor division, so 104 / 15 = 6.93 becomes 6 before rounding.
- **Failing test:** `test_3_report.TestReport.test_summary`
- **Unblocks:** test_summary.

Fix:

```diff
-        "tokens_per_doc": round(total_tokens // len(embedded), 2) if embedded else None,
+        "tokens_per_doc": round(total_tokens / len(embedded), 2) if embedded else None,
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_summary`):

```
AssertionError: {'emb[60 chars]c': 6, 'by_collection': {'faq': 6, 'legal': 3, 'support': 6}} != {'emb[60 chars]c': 6.93, 'by_collection': {'faq': 6, 'legal':[13 chars]: 6}}
  {'by_collection': {'faq': 6, 'legal': 3, 'support': 6},
   'embedded': 15,
   'failed': 6,
-  'tokens_per_doc': 6,
+  'tokens_per_doc': 6.93,
?                     +++

   'total_tokens': 104}
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `embedclient/retry.py` → `retry_delay`: Header names are lower-cased before the lookup, so 'Retry-After' is found whatever the case; float() accepts the fractional '0.3'; and backoff_s * 2 ** attempt with attempt starting at 0 is exactly the README formula (0.05, then 0.1).
- `embedclient/transport.py` → `send_sync`: urlopen raises HTTPError for 4xx/5xx; catching it and returning a Response with err.code keeps the status for the retry logic instead of turning it into an exception.
