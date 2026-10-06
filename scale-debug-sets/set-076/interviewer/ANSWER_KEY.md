# set-076 answer key: Async embedding backfill: concurrency cap, retries, commit, paged index check

**Domain:** endpoint_client  |  **Length:** FULL  |  **Difficulty:** hard

**Format:** one bug per failing test. Fixing a bug makes exactly its test pass.

| Failing test | Bug |
|---|---|
| `test_1_requests.TestRequests.test_concurrency_limit` | B1 Semaphore created but never acquired |
| `test_1_requests.TestRequests.test_attempts_per_batch` | B2 One attempt short on persistent 5xx |
| `test_2_batches.TestBatches.test_backoff_delays` | B3 Retry-After: 0 replaced by exponential backoff |
| `test_2_batches.TestBatches.test_job_committed` | B4 Commit coroutine never awaited |
| `test_3_report.TestReport.test_index_coverage` | B5 Index offset advanced by requested page size |
| `test_3_report.TestReport.test_requeue` | B6 Requeue statuses listed as strings |

## Failing pattern with all bugs present

- `tests.test_1_requests.TestRequests.test_attempts_per_batch`
- `tests.test_1_requests.TestRequests.test_concurrency_limit`
- `tests.test_2_batches.TestBatches.test_backoff_delays`
- `tests.test_2_batches.TestBatches.test_job_committed`
- `tests.test_3_report.TestReport.test_index_coverage`
- `tests.test_3_report.TestReport.test_requeue`

## Bugs (recommended order)

### B1: Semaphore created but never acquired

- **Type:** semaphore-unused
- **Symptom:** Test 1 test_concurrency_limit: `8 != 2`. The server saw all 8 batches in flight at once. Every result and report field is still correct.
- **Location:** `vecsync/client.py` → `EmbeddingClient.embed_batch`
- **Why it fails:** A new Semaphore is built on every call, so each batch acquires its own private semaphore and never waits. The shared `self._slots` from __init__ is never used, and all 8 batches hit the server at once.
- **Failing test:** `test_1_requests.TestRequests.test_concurrency_limit`
- **Unblocks:** test_concurrency_limit

Fix:

```diff
-        async with asyncio.Semaphore(self.config.max_concurrency):
+        async with self._slots:
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_concurrency_limit`):

```
AssertionError: 8 != 2
```

### B2: One attempt short on persistent 5xx

- **Type:** retry-off-by-one
- **Symptom:** Test 1 test_attempts_per_batch: policies-01 shows 3 attempts instead of 4. Its result is still failed/503 and the backoff delays are unchanged.
- **Location:** `vecsync/retry.py` → `send_with_retries`
- **Why it fails:** max_retries counts retries, not attempts, so the loop needs max_retries + 1 iterations. With range(max_retries) a batch that keeps failing gets only 3 attempts. The last sleep still happens, so the backoff list looks unchanged.
- **Failing test:** `test_1_requests.TestRequests.test_attempts_per_batch`
- **Unblocks:** test_attempts_per_batch

Fix:

```diff
-    for attempt in range(max_retries):
+    for attempt in range(max_retries + 1):
```

Observed with only this bug applied (`tests.test_1_requests.TestRequests.test_attempts_per_batch`):

```
AssertionError: {'faq[45 chars]01': 3, 'policies-02': 2, 'changelog-01': 1, '[29 chars]': 1} != {'faq[45 chars]01': 4, 'policies-02': 2, 'changelog-01': 1, '[29 chars]': 1}
  {'changelog-01': 1,
   'changelog-02': 1,
   'faq-01': 1,
   'faq-02': 3,
   'faq-03': 1,
-  'policies-01': 3,
?                 ^

+  'policies-01': 4,
?                 ^

   'policies-02': 2,
   'pricing-01': 1}
```

### B3: Retry-After: 0 replaced by exponential backoff

- **Type:** falsy-zero
- **Symptom:** Test 2 test_backoff_delays: `[0.5, 0.5, 0.5, 1.0, 1.0, 2.0] != [0.0, 0.0, 0.5, 0.5, 1.0, 2.0]`. faq-02 waits 0.5 and 1.0 although the server sent `Retry-After: 0`.
- **Location:** `vecsync/retry.py` → `backoff_delay`
- **Why it fails:** parse_retry_after returns 0.0 for `Retry-After: 0`, and `0.0 or ...` falls through to the exponential formula. faq-02 waits 0.5 and 1.0 instead of 0 and 0.
- **Failing test:** `test_2_batches.TestBatches.test_backoff_delays`
- **Unblocks:** test_backoff_delays

Fix:

```diff
-    return parse_retry_after(response.headers) or base * (2 ** attempt)
+    hint = parse_retry_after(response.headers)
+    if hint is not None:
+        return hint
+    return base * (2 ** attempt)
```

Observed with only this bug applied (`tests.test_2_batches.TestBatches.test_backoff_delays`):

```
AssertionError: Lists differ: [0.5, 0.5, 0.5, 1.0, 1.0, 2.0] != [0.0, 0.0, 0.5, 0.5, 1.0, 2.0]

First differing element 0:
0.5
0.0

- [0.5, 0.5, 0.5, 1.0, 1.0, 2.0]
+ [0.0, 0.0, 0.5, 0.5, 1.0, 2.0]
```

### B4: Commit coroutine never awaited

- **Type:** missing-await
- **Symptom:** Test 2 test_job_committed: `[] != [{'job_id': 'backfill-0412', 'accepted': [...], 'documents': 10}]`. The server never receives a commit, and a 'coroutine ... was never awaited' RuntimeWarning is printed.
- **Location:** `vecsync/runner.py` → `run_job`
- **Why it fails:** Calling an async function only creates a coroutine object. Without await it never runs, so no commit request is sent. Python just prints a 'coroutine was never awaited' RuntimeWarning.
- **Failing test:** `test_2_batches.TestBatches.test_job_committed`
- **Unblocks:** test_job_committed

Fix:

```diff
-    client.commit(accepted, documents_ok)
+    await client.commit(accepted, documents_ok)
```

Observed with only this bug applied (`tests.test_2_batches.TestBatches.test_job_committed`):

```
AssertionError: Lists differ: [] != [{'job_id': 'backfill-0412', 'accepted': [[74 chars] 10}]

Second list contains 1 additional elements.
First extra element 0:
{'job_id': 'backfill-0412', 'accepted': ['changelog-02', 'faq-01', 'faq-02', 'faq-03', 'policies-02'], 'documents': 10}

- []
+ [{'accepted': ['changelog-02', 'faq-01', 'faq-02', 'faq-03', 'policies-02'],
+   'documents': 10,
+   'job_id' ...
```

### B5: Index offset advanced by requested page size

- **Type:** pagination-cursor
- **Symptom:** Test 3 test_index_coverage: faq shows `{'stored': 6, 'missing': ['faq-004', 'faq-005']}` instead of `{'stored': 9, 'missing': []}`. The other collections are correct.
- **Location:** `vecsync/index.py` → `collect_index`
- **Why it fails:** The service caps pages at 3 items even though the client asks for 5, so stepping the offset by 5 skips ids 4-5 of every page. Only faq has more than one page, so only faq loses vectors.
- **Failing test:** `test_3_report.TestReport.test_index_coverage`
- **Unblocks:** test_index_coverage

Fix:

```diff
-        offset += client.config.page_size
+        offset += len(items)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_index_coverage`):

```
AssertionError: {'faq': {'stored': 6, 'missing': ['faq-004', 'faq-005']}, 'p[118 chars] []}} != {'faq': {'stored': 9, 'missing': []}, 'policies': {'stored':[98 chars] []}}
  {'changelog': {'missing': [], 'stored': 1},
-  'faq': {'missing': ['faq-004', 'faq-005'], 'stored': 6},
?                      --------------------             ^

+  'faq': {'missing': [], 'stored': 9},
?                       ...
```

### B6: Requeue statuses listed as strings

- **Type:** enum-vs-string
- **Symptom:** Test 3 test_requeue: `[] != ['chg-201', 'chg-202', 'chg-203', 'pol-101', ...]`. Nothing is requeued, even though counts shows 2 failed and 1 rejected.
- **Location:** `vecsync/models.py` → `REQUEUE_STATUSES`
- **Why it fails:** BatchStatus is a plain Enum, so BatchStatus.FAILED == "failed" is False and nothing matches. The counts still look right because they compare `.value`.
- **Failing test:** `test_3_report.TestReport.test_requeue`
- **Unblocks:** test_requeue

Fix:

```diff
-REQUEUE_STATUSES = ("failed", "rejected")
+REQUEUE_STATUSES = (BatchStatus.FAILED, BatchStatus.REJECTED)
```

Observed with only this bug applied (`tests.test_3_report.TestReport.test_requeue`):

```
AssertionError: Lists differ: [] != ['chg-201', 'chg-202', 'chg-203', 'pol-101[52 chars]303']

Second list contains 9 additional elements.
First extra element 0:
'chg-201'

- []
+ ['chg-201',
+  'chg-202',
+  'chg-203',
+  'pol-101',
+  'pol-103',
+  'pol-104',
+  'prc-301',
+  'prc-302',
+  'prc-303']
```

## Red herrings (marked `# VERIFIED`, genuinely correct)

- `vecsync/transport.py` → `perform_request`: Returning error statuses as a Response instead of raising looks like it ignores HTTP failures, but the retry layer and interpret() both branch on response.status. Raising here would make retries impossible.
- `vecsync/loader.py` → `make_batches`: `-(-len(docs) // size)` is ceiling division, so a 7-document collection gives 3 batches and the slices cover every document exactly once. sorted() is stable, so equal dates keep file order as the spec requires.
