# set-092 answer key: Async embedding index sync: batches, concurrency, retries, paginated index

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_embedding_request_body` | B1 Datetimes encoded with str() instead of ISO 8601 |
| `test_1_requests.TestRequests.test_concurrency_limit` | B2 Fresh semaphore per request |
| `test_1_requests.TestRequests.test_backoff_delays` | B3 Backoff sleep never awaited |
| `test_2_sync.TestSync.test_index_entries_to_delete` | B4 Last page of the index listing dropped |
| `test_3_summary.TestSummary.test_status_counts` | B5 Failed batches filtered out of the gather results |
| `test_3_summary.TestSummary.test_cost` | B6 Integer division in the cost |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_backoff_delays`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_1_requests.TestRequests.test_embedding_request_body`
- `tests.test_2_sync.TestSync.test_index_entries_to_delete`
- `tests.test_3_summary.TestSummary.test_cost`
- `tests.test_3_summary.TestSummary.test_status_counts`

## Bugs (recommended order)

### B1: Datetimes encoded with str() instead of ISO 8601

- **Type:** json-serialization
- **Symptom:** Test 1 test_embedding_request_body: the faq-0 body differs only in documents[].updated_at, which arrives as '2026-09-01 10:00:00' (space) instead of '2026-09-01T10:00:00'.
- **Location:** `embedsync/transport.py` → `_json_default`
- **Why it fails:** json.dumps calls the default hook for datetimes. str(datetime) puts a space between date and time ('2026-09-01 10:00:00'), so the body no longer carries ISO 8601 as the spec requires. Nothing crashes; the server just gets a different string.
- **Failing test:** `test_1_requests.TestRequests.test_embedding_request_body`
- **Unblocks:** test_embedding_request_body.

Fix:

```diff
-        return str(value)
+        return value.isoformat()
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_embedding_request_body`):

```
AssertionError: {'mod[212 chars]09-01 10:00:00'}, {'id': 'f02', 'updated_at': [106 chars]-0'}} != {'mod[212 chars]09-01T10:00:00'}, {'id': 'f02', 'updated_at': [106 chars]-0'}}
Diff is 1011 characters long. Set self.maxDiff to None to see it.
```

### B2: Fresh semaphore per request

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_limit: the mock server saw 6 embedding requests in flight at once ('6 not less than or equal to 2'). Every result is still correct.
- **Location:** `embedsync/client.py` → `EmbeddingClient._bounded`
- **Why it fails:** Each task acquires its own brand-new semaphore, so it never waits for anyone. The shared self._limit is created in embed_all but never acquired, so all six batches run at once.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** test_concurrency_limit.

Fix:

```diff
-        async with asyncio.Semaphore(self.config.max_concurrency):
+        async with self._limit:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 6 not less than or equal to 2
```

### B3: Backoff sleep never awaited

- **Type:** missing-await
- **Symptom:** Test 1 test_backoff_delays: no delays recorded ([] instead of [0.25, 0.5, 0.5, 1.0]), with a 'coroutine ... was never awaited' RuntimeWarning. Attempt counts are unchanged.
- **Location:** `embedsync/retry.py` → `with_retries`
- **Why it fails:** Calling an async function without await only creates a coroutine object; its body never runs. So the retry loop goes straight to the next attempt without waiting, and Python prints a 'coroutine was never awaited' RuntimeWarning.
- **Failing test:** `test_1_requests.TestRequests.test_backoff_delays`
- **Unblocks:** test_backoff_delays.

Fix:

```diff
-        sleep(policy.delay(attempt, response))
+        await sleep(policy.delay(attempt, response))
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_backoff_delays`):

```
AssertionError: Lists differ: [] != [0.25, 0.5, 0.5, 1.0]

Second list contains 4 additional elements.
First extra element 0:
0.25

- []
+ [0.25, 0.5, 0.5, 1.0]
```

### B4: Last page of the index listing dropped

- **Type:** pagination-cursor
- **Symptom:** Test 2 test_index_entries_to_delete: to_delete is ['p41', 'p42', 'p43'], so p06 and p88 are missing. The request log still shows all three policies pages.
- **Location:** `embedsync/index.py` → `list_index`
- **Why it fails:** The loop breaks on the last page before adding its items, so the final page of every collection is lost. All three pages are still requested, so the request log looks normal. Only policies has a multi-page index, and its last page holds p06 and p88, which should be deleted.
- **Failing test:** `test_2_sync.TestSync.test_index_entries_to_delete`
- **Unblocks:** test_index_entries_to_delete.

Fix:

```diff
+        items.extend(page["items"])
         token = page.get("next_page_token")
         if not token:
             break
-        items.extend(page["items"])
```

Observed with only this bug applied (`tests.test_2_sync.TestSync.test_index_entries_to_delete`):

```
AssertionError: Lists differ: ['p41', 'p42', 'p43'] != ['p06', 'p41', 'p42', 'p43', 'p88']

First differing element 0:
'p41'
'p06'

Second list contains 2 additional elements.
First extra element 3:
'p43'

- ['p41', 'p42', 'p43']
+ ['p06', 'p41', 'p42', 'p43', 'p88']
?  +++++++                   +++++++
```

### B5: Failed batches filtered out of the gather results

- **Type:** gather-hides-failures
- **Symptom:** Test 3 test_status_counts: counts show failed 0 (not 3) and failed_batches is {} (not {'products-1': 503}). x04, x05 and x07 just disappear from outcomes, with no error anywhere.
- **Location:** `embedsync/client.py` → `EmbeddingClient.embed_all`
- **Why it fails:** return_exceptions=True turns the BatchError into a value, and the filter then throws it away. run_sync never sees the failure, so products-1's documents get no outcome at all and failed_batches is empty. (It also shifts zip(batches, outcomes), which only stays harmless because the failing batch is last.)
- **Failing test:** `test_3_summary.TestSummary.test_status_counts`
- **Unblocks:** test_status_counts.

Fix:

```diff
-        outcomes = await asyncio.gather(*(self._bounded(b) for b in batches), return_exceptions=True)
-        return [o for o in outcomes if not isinstance(o, Exception)]
+        return await asyncio.gather(*(self._bounded(b) for b in batches), return_exceptions=True)
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_status_counts`):

```
AssertionError: Tuples differ: ({'embedded': 12, 'skipped': 4, 'failed': 0}, {}) != ({'embedded': 12, 'skipped': 4, 'failed': 3}, {'products-1': 503})

First differing element 0:
{'embedded': 12, 'skipped': 4, 'failed': 0}
{'embedded': 12, 'skipped': 4, 'failed': 3}

- ({'embedded': 12, 'failed': 0, 'skipped': 4}, {})
?                             ^

+ ({'embedded': 12, 'failed': 3, 'skipped': 4}, ...
```

### B6: Integer division in the cost

- **Type:** integer-division
- **Symptom:** Test 3 test_cost: cost_usd is 0.0 instead of 0.0118, while total_tokens (91) is right.
- **Location:** `embedsync/reports.py` → `summarize`
- **Why it fails:** `//` floors the token count to whole thousands before pricing. With 91 tokens that is 0, so the cost is 0.0 instead of 0.0118.
- **Failing test:** `test_3_summary.TestSummary.test_cost`
- **Unblocks:** test_cost.

Fix:

```diff
-        "cost_usd": round(result.total_tokens // 1000 * config.price_per_1k_tokens, 4),
+        "cost_usd": round(result.total_tokens / 1000 * config.price_per_1k_tokens, 4),
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_cost`):

```
AssertionError: 0.0 != 0.0118
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `embedsync/documents.py` → `latest_by_id`: The `>=` looks like it lets an equal timestamp overwrite, and it does, which is the spec: on equal timestamps the later row in the file wins. It compares parsed datetimes, so the three formats order correctly.
- `embedsync/transport.py` → `_send_sync`: Catching HTTPError looks like it swallows failures, but it turns them into a Response carrying the real status code, which the retry loop and embed_batch then check. Nothing is lost.
