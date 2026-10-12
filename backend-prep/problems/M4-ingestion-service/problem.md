# M4. Ingestion service

Customers send us batches of text (support tickets, chat logs) to be labeled
by a model. Build the small FastAPI service in front of that pipeline: it
accepts JSONL uploads, stores them durably, labels every row in the background
with a flaky LLM-like classifier, and reports progress. It must survive restarts
and impatient clients who press the button twice.

## Input

`data/rows.jsonl` (`SAMPLE_JSONL` in `problem_api`): one JSON object per line.

```
{"id": "r1", "text": "The product arrived broken and support never answered.", "source": "zendesk"}
{"id": "r3", "text": "[flaky] Shipping was fine I guess."}
{"text": "no id here"}
{"id": "r6", "text": "Refund took three weeks. Terrible.
```

## Part 1: upload and store (about 20 minutes)

### Setup

```python
from problem_api import SAMPLE_JSONL, flaky_classifier    # SAMPLE_JSONL is a pathlib.Path
with TestClient(create_app(tmp_dir, flaky_classifier())) as client:   # fastapi.testclient
    client.post("/batches", files={"file": ("rows.jsonl", SAMPLE_JSONL.read_bytes())})
```

Tests do exactly this: a fresh `create_app(tmp_path / "store", classifier)` wrapped in `TestClient(...)` as a context manager (so startup/shutdown run).
Your file starts empty; the `if __name__ == "__main__":` block is what the Run button executes (print the raw lines, then try your endpoints).

### Contract (Part 1)

* `create_app(storage_dir: str | Path, classifier: Callable[[str], str] | None = None) -> FastAPI` — the only name tests import; `classifier` is unused (and may be `None`) until Part 2.
* Routes: `POST /batches` (201 / 400 / 422), `GET /batches/{batch_id}`, `GET /batches/{batch_id}/rows` (404 for unknown ids).

All state lives in an **SQLite** database inside `storage_dir` (create the
directory if needed). Another `create_app` over the same directory sees everything.

**`POST /batches`**: multipart upload, field `file`, a JSONL file.

* Decode as UTF-8 (not UTF-8 → **400**). Split into lines (`line` is 1-based);
  whitespace-only lines are skipped.
* Each line is checked in this order; the first failure is its error:
  `invalid_json`, `not_an_object`, `missing_id` (`id` is not a non-empty string),
  `missing_text` (`text` is not a string with non-whitespace content),
  `duplicate_id` (an earlier valid line in this file has that `id`). Other keys are ignored.
* No valid rows at all → **422** `{"detail": "no valid rows", "errors": [...]}`.
* Otherwise store the batch and its valid rows (upload order) and return **201**
  `{"batch_id": "b_…", "accepted": 5, "rejected": 5, "errors": [{"line": 5, "error": "missing_text"}, ...]}`
  (`errors` in line order).

**`GET /batches/{batch_id}`** → `{"batch_id", "row_count", "counts": {"pending": n, "done": n, "failed": n}}`.

**`GET /batches/{batch_id}/rows`** → `{"rows": [{"id", "text", "status", "label",
"attempts", "error"}, ...]}` in upload order. A new row is
`{"status": "pending", "label": null, "attempts": 0, "error": null}`.

Unknown ids are **404** `{"detail": "batch not found"}` (or `"job not found"`).

<!-- part 2 -->

## Part 2: background labeling (about 20 minutes)

### Contract (Part 2)

* `from problem_api import RetryableError` — an `Exception` subclass the classifier raises for transient failures (catch it by this class).
* `classifier(text: str) -> str` — now used; tests pass plain callables (`flaky_classifier()`, `keyword_label`, ...).
* New routes: `POST /batches/{batch_id}/process` (202, 404) and `GET /jobs/{job_id}` (404 `{"detail": "job not found"}`).

**`POST /batches/{batch_id}/process`** → **202** with the job object (same shape as
`GET /jobs/{id}` below, `"status": "queued"`) (404 for an unknown batch). The job covers the batch's rows that are `pending`
at that moment.

* A **background worker thread** (not the request thread) runs jobs one at a
  time, in the order they were created, and each job's rows in upload order.
  The request returns immediately.
* For each row call `classifier(text)`. It returns a label, or raises:
  * `RetryableError` (from `problem_api`): try again, at most **3 attempts** in
    total, no waiting;
  * any other `Exception`: permanent, no more attempts.
* Success: `status "done"`, `label`, `attempts` = attempts used, `error null`.
  Failure: `status "failed"`, `label null`, `attempts`, `error` = `str(exc)` of
  the last exception. One bad row never stops the job or the worker.
* Record each row's outcome as soon as it is known (clients watch progress).

**`GET /jobs/{job_id}`** → `{"job_id": "j_…", "batch_id": "b_…", "status": "running", "total": 5, "done": 2, "failed": 0}`.

`status` goes `queued` → `running` → `completed` (a job is `completed` even if
some rows failed). `total` = rows in the job; `done` / `failed` = its rows finished so far.

<!-- part 3 -->

## Part 3: restarts and double clicks (about 20 minutes)

### Contract (Part 3)

No new names or routes: same `create_app`, and `POST /batches/{id}/process` gains the 200 responses below.

* **Restarts lose nothing.** When `create_app` starts over an existing
  directory, every job that is `queued` or `running` is resumed **under the same
  `job_id`**, in creation order. Rows already `done`/`failed` are never
  classified again; only `pending` rows are.
* **Idempotent process.** `POST /batches/{id}/process`:
  * if the batch already has a `queued` or `running` job → **200** with that job
    (same `job_id`, no new job);
  * else if it has no `pending` rows → **200** `{"job_id": null, "status": "nothing_to_do"}`;
  * else → **202** with a new job (Part 2).
  This must hold under **concurrent** identical requests: exactly one gets 202,
  all get the same `job_id`.
* **No "database is locked".** Concurrent uploads, polls and the worker's
  writes must never produce a 5xx.
* Exceptions that are not `Exception` subclasses (e.g. `SystemExit`) are not
  yours to handle: let them propagate. Tests raise one inside the classifier to
  simulate the process dying mid-job.

## Constraints

* Standard library `sqlite3` only (no ORM needed). One worker thread is enough.
* Never hold a database lock or transaction while calling the classifier.
* Tests use `fastapi.testclient.TestClient(app)` as a context manager and poll
  `GET /jobs/{id}` with a timeout.

<details><summary>Hint 1</summary>

Give each row a `job_id` column, set when the job is created. Then job progress
is a `COUNT(*) ... GROUP BY status`, and resuming a job is "process its rows
that are still pending", which is restart-proof by construction.
</details>

<details><summary>Hint 2</summary>

A `threading.Lock` around every short DB operation (open connection, statement,
commit, close) is the simplest way to rule out "database is locked" in one
process; the check-and-create of a job must happen inside one such section.
</details>

## Discussion (talk it through)

* Two instances of this service share one database. What breaks (resume,
  "one job per batch")? How would leases / heartbeats or `SELECT ... FOR UPDATE
  SKIP LOCKED` in Postgres fix it?
* A row was being classified when the process died. You will classify it again:
  what does that cost, and when is at-least-once processing not acceptable?
* The model provider rate-limits you to 50 requests/s and the queue is 2M rows
  deep. How do you size workers, retry with backoff, and keep `GET /jobs` honest?
