# set-020 answer key: Async batch labeling client: concurrency, pages and archive

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** easy

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_1_concurrency_limit` | B1 Semaphore created but never acquired |
| `test_1_requests.TestRequests.test_2_every_batch_archived` | B2 archive() coroutine never awaited |
| `test_2_results.TestResults.test_3_shard_s2_all_pages` | B3 Last results page never fetched |
| `test_2_results.TestResults.test_4_shard_s3_review_threshold` | B4 Score equal to the threshold sent to review |
| `test_2_results.TestResults.test_5_shard_s5` | B5 Request ids trimmed but not upper-cased |
| `test_3_summary.TestSummary.test_6_cost` | B6 Tokens rounded to whole thousands before pricing |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_1_concurrency_limit`
- `tests.test_1_requests.TestRequests.test_2_every_batch_archived`
- `tests.test_2_results.TestResults.test_3_shard_s2_all_pages`
- `tests.test_2_results.TestResults.test_4_shard_s3_review_threshold`
- `tests.test_2_results.TestResults.test_5_shard_s5`
- `tests.test_3_summary.TestSummary.test_6_cost`

## Bugs (recommended order)

### B1: Semaphore created but never acquired

- **Type:** semaphore-unused
- **Symptom:** test_1_concurrency_limit fails: AssertionError: 5 not less than or equal to 2 (all five shards submit at once). Every result and summary value is still right.
- **Location:** `labelbatch/pipeline.py` → `run_shard`
- **Why it fails:** run_all builds a Semaphore(max_concurrency) and passes it down, but run_shard never enters it, so gather starts all five shards at once and the server sees five submits in flight together.
- **Failing test:** `test_1_requests.TestRequests.test_1_concurrency_limit`
- **Unblocks:** test_1_concurrency_limit.

Fix:

```diff
-    return await process_shard(client, shard, items)
+    async with limit:
+        return await process_shard(client, shard, items)
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_1_concurrency_limit`):

```
AssertionError: 5 not less than or equal to 2
```

### B2: archive() coroutine never awaited

- **Type:** missing-await
- **Symptom:** test_2_every_batch_archived fails: the server's archived list is [] instead of all five batch ids, and a RuntimeWarning "coroutine 'BatchClient.archive' was never awaited" appears on stderr.
- **Location:** `labelbatch/pipeline.py` → `process_shard`
- **Why it fails:** Calling an async def without await only creates a coroutine object; it never runs, so no DELETE is sent. Python prints a 'coroutine ... was never awaited' RuntimeWarning when the object is garbage collected.
- **Failing test:** `test_1_requests.TestRequests.test_2_every_batch_archived`
- **Unblocks:** test_2_every_batch_archived.

Fix:

```diff
-    client.archive(batch_id)
+    await client.archive(batch_id)
     return outcome
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_2_every_batch_archived`):

```
AssertionError: Lists differ: [] != ['batch_s1', 'batch_s2', 'batch_s3', 'batch_s4', 'batch_s5']

Second list contains 5 additional elements.
First extra element 0:
'batch_s1'

- []
+ ['batch_s1', 'batch_s2', 'batch_s3', 'batch_s4', 'batch_s5']
```

### B3: Last results page never fetched

- **Type:** pagination-cursor
- **Symptom:** test_3_shard_s2_all_pages fails: R10 (the only result on S2's third page) has status missing with label/score None instead of labeled dog 0.86.
- **Location:** `labelbatch/client.py` → `BatchClient.fetch_results`
- **Why it fails:** range's stop is exclusive, so pages 2..total_pages-1 are read and the last page is skipped. Only S2 has more than one page (7 results at page_size 3), so only R10 goes missing.
- **Failing test:** `test_2_results.TestResults.test_3_shard_s2_all_pages`
- **Unblocks:** test_3_shard_s2_all_pages.

Fix:

```diff
-        for page in range(2, first["total_pages"]):
+        for page in range(2, first["total_pages"] + 1):
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_3_shard_s2_all_pages`):

```
AssertionError: {'R04[471 chars]rd': 'S2', 'status': 'missing', 'label': None, 'score': None}} != {'R04[471 chars]rd': 'S2', 'status': 'labeled', 'label': 'dog', 'score': 0.86}}
  {'R04': {'label': 'dog', 'score': 0.91, 'shard': 'S2', 'status': 'labeled'},
   'R05': {'label': 'bird', 'score': 0.77, 'shard': 'S2', 'status': 'labeled'},
   'R06': {'label': 'cat', 'score': 0.83, 'shard': 'S2', 'statu ...
```

### B4: Score equal to the threshold sent to review

- **Type:** off-by-one
- **Symptom:** test_4_shard_s3_review_threshold fails: R12 (score exactly 0.7) is needs_review instead of labeled.
- **Location:** `labelbatch/pipeline.py` → `classify`
- **Why it fails:** The spec labels any score >= review_threshold. With `>`, R12's score of exactly 0.7 is routed to review.
- **Failing test:** `test_2_results.TestResults.test_4_shard_s3_review_threshold`
- **Unblocks:** test_4_shard_s3_review_threshold.

Fix:

```diff
-    status = "labeled" if score > threshold else "needs_review"
+    status = "labeled" if score >= threshold else "needs_review"
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_4_shard_s3_review_threshold`):

```
AssertionError: {'R11[102 chars]s': 'needs_review', 'label': 'cat', 'score': 0[80 chars].69}} != {'R11[102 chars]s': 'labeled', 'label': 'cat', 'score': 0.7}, [75 chars].69}}
  {'R11': {'label': 'bird', 'score': 0.93, 'shard': 'S3', 'status': 'labeled'},
-  'R12': {'label': 'cat', 'score': 0.7, 'shard': 'S3', 'status': 'needs_review'},
?                                                              ...
```

### B5: Request ids trimmed but not upper-cased

- **Type:** id-normalization
- **Symptom:** test_5_shard_s5 fails: the S5 rows contain `r17` with label unknown, score 0.0, status needs_review, and no `R17` entry.
- **Location:** `labelbatch/loader.py` → `load_requests`
- **Why it fails:** `r17` is sent and reported as lower-case. The API doesn't recognise that id, so it returns label `unknown` with score 0.0, and the report key is `r17` instead of `R17`.
- **Failing test:** `test_2_results.TestResults.test_5_shard_s5`
- **Unblocks:** test_5_shard_s5.

Fix:

```diff
-            item = {"id": clean(row["request_id"]), "text": clean(row["text"])}
+            item = {"id": norm_id(row["request_id"]), "text": clean(row["text"])}
```

Observed with only this bug applied (`tests.test_2_results.TestResults.test_5_shard_s5`):

```
AssertionError: {'R16[71 chars], 'R18': {'shard': 'S5', 'status': 'skipped', [264 chars]0.0}} != {'R16[71 chars], 'R17': {'shard': 'S5', 'status': 'labeled', [256 chars]one}}
Diff is 754 characters long. Set self.maxDiff to None to see it.
```

### B6: Tokens rounded to whole thousands before pricing

- **Type:** float-rounding
- **Symptom:** test_6_cost fails: cost_usd is 0.18 instead of 0.1763. total_tokens (8815) still passes.
- **Location:** `labelbatch/reports.py` → `summarize`
- **Why it fails:** round(tokens / 1000) rounds 8.815 thousand tokens up to 9 before multiplying, so the cost is 0.18 instead of 0.1763. Rounding has to be the last step, at 4 decimals.
- **Failing test:** `test_3_summary.TestSummary.test_6_cost`
- **Unblocks:** test_6_cost.

Fix:

```diff
-        "cost_usd": round(tokens / 1000) * config.price_per_1k_tokens,
+        "cost_usd": round(tokens * config.price_per_1k_tokens / 1000, 4),
```

Observed with only this bug applied (`tests.test_3_summary.TestSummary.test_6_cost`):

```
AssertionError: 0.18 != 0.1763
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `labelbatch/transport.py` → `_blocking_send`: It is the blocking urllib call that `send` runs in a worker thread via asyncio.to_thread. HTTP errors are caught and returned as Response objects with their status, headers and decoded body, so callers can check the status themselves.
- `labelbatch/client.py` → `poll_delay`: Returning 0 for attempt 0 looks like it ignores the interval, but it only skips the wait before the first poll. Every later poll waits poll_interval_s, so there are exactly max_polls status calls spaced as rule 2 says.
