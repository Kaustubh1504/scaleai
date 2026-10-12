# 34. Concurrent fetch with partial failures

Every night a job pulls metadata for a batch of customer **documents** before
they're sent out for annotation. The Documents API is flaky: some ids are gone
(404), the server occasionally 5xxs, and some calls time out. One bad document
must **not** sink the batch: fetch everything concurrently, collect what
worked, and report exactly what didn't. But a genuine **bug** must still crash
loudly, not get filed as "a failure".

## The API

`GET /v1/documents/{doc_id}` → `200`

```json
{"id": "doc_007", "title": "Contract 7", "pages": 5,
 "customer_id": "cus_3", "storage_url": "s3://docs/doc_007.pdf"}
```

Failures you'll see: `404`, `403`, `500`/`503`, `httpx.ReadTimeout`,
`httpx.ConnectError`.

## Setup

```python
from problem_api import make_api
api = make_api(n_docs=20)                                  # doc_001 .. doc_020 exist
api.script("GET /v1/documents/doc_002", [503, "timeout"])  # also 404, 403, 500, "connect"
client = api.client()
```

`make_api(..., broken=("doc_003",))` makes that id's 2xx record come back
without `"title"`. The `if __name__ == "__main__":` block is what the Run
button executes: print what each kind of failure looks like there.

## Your task

Your module must define:

* `fetch_documents(client: httpx.Client, doc_ids: list[str], max_workers: int = 8) -> dict`

Use **threads** (`ThreadPoolExecutor(max_workers)`, sharing the one client).
Fetch every id once (no duplicates in the input) and return a dict with two keys:

* `"results"`: `{doc_id: {"id", "title", "pages"}}`, only those three keys from the body.
* `"failures"`: a list of `{"id": doc_id, "error_type": str, "message": str}`, sorted by id.

Every input id ends up in exactly one of the two. `error_type` is:

| cause | `error_type` | retried? |
|---|---|---|
| 404 | `"not_found"` | no |
| any 5xx | `"server_error"` | **once**, immediately; if the retry succeeds it's a result |
| `httpx.TimeoutException` | `"timeout"` | no |
| any other non-2xx, or any other `httpx.HTTPError` (e.g. `ConnectError`) | `"other"` | no |

* `message` is a non-empty human-readable string (e.g. `str(exc)`).
* A failure for one id never stops or cancels the others.
* **Swallow only** `httpx.HTTPError` and non-2xx statuses. Anything else is
  a bug and must **propagate** out of `fetch_documents`. In particular, a 2xx
  record missing `id`, `title` or `pages` raises `KeyError` (don't catch it).
* `[]` returns `{"results": {}, "failures": []}`.

## Example

```python
api = make_api(n_docs=5)
api.script("GET /v1/documents/doc_002", [503, 503])
api.script("GET /v1/documents/doc_004", ["timeout"])
fetch_documents(api.client(), ["doc_001", "doc_002", "doc_003", "doc_004", "doc_404"])
# {"results": {"doc_001": {...}, "doc_003": {...}},
#  "failures": [{"id": "doc_002", "error_type": "server_error", "message": "503 ..."},
#               {"id": "doc_004", "error_type": "timeout", "message": "..."},
#               {"id": "doc_404", "error_type": "not_found", "message": "..."}]}
```

## Constraints

* Go through HTTP only (don't read `api.docs`). No sleeping between retries.

<details><summary>Hint 1</summary>

Make the worker return an outcome (ok + record, or fail + failure dict) instead
of raising for expected failures. Then the main thread just sorts outcomes into the two buckets. Bugs still raise, and
`future.result()` / `pool.map` re-raises them in the main thread.
</details>

<details><summary>Hint 2</summary>

Order your `except` clauses from specific to general: `httpx.TimeoutException`
is a subclass of `httpx.HTTPError`. Never write `except Exception:` around the
whole worker: that's how the `KeyError` gets swallowed.
</details>

## Follow-up (talk it through)

* The batch is 50k ids and 30% time out. What do you change (retry budget,
  backoff, circuit breaker)?
* How would you make re-runs only retry the failures? What would you persist?
* Threads vs `asyncio.gather(return_exceptions=True)` for this job: trade-offs?
