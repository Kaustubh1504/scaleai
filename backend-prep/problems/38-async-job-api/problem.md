# 38. Async job API with background workers

Some annotation-quality checks take minutes, far too long to run inside an
HTTP request. The usual fix: `POST` a job, get a `job_id` back immediately,
and poll for the result while a pool of background workers does the work.
Build that service with a `queue.Queue` and worker threads.

## The API you build

`POST /jobs` with a JSON object. `kind` picks the job; the other keys are its input:

```json
{"kind": "word_count", "text": "the quick  brown\nfox"}
{"kind": "sum", "numbers": [1, 2, 3.5]}
```

→ **`202`** `{"job_id": "…", "status": "queued"}` (always `"queued"` in this
response, even if a worker grabs it instantly). A body that isn't an object,
or whose `kind` isn't `"word_count"` or `"sum"`, is **422**.

`GET /jobs/{job_id}` → `200`, or `404` for an unknown id:

```json
{"job_id": "…", "kind": "word_count", "status": "done", "result": 4, "error": null}
```

`status` is `queued` → `running` → `done` | `failed`. `result` and `error`
are always present and `null` unless set.

`GET /jobs?status=<status>` → `200` `{"jobs": [...]}`, every job (or only
those with that status) as above, in **submission order**. An unknown status
is 422.

## Setup

```python
with TestClient(create_app(workers=1, process=my_fn)) as c:   # `with` runs the lifespan (your workers)
    job_id = c.post("/jobs", json={"kind": "sum", "numbers": [1, 2]}).json()["job_id"]
```

Tests build the app exactly like this, sometimes injecting a `process` that blocks
until released. Your file starts empty. An `if __name__ == "__main__":` block is
what the Run button executes: use it to submit a job, sleep briefly, and list jobs.

## Your task

Write in your file:

* `run_job(payload: dict) -> Any`: the default processor.
* `create_app(storage_dir: str | Path | None = None, workers: int = 2, process: Callable[[dict], Any] | None = None) -> FastAPI`
* Routes: `POST /jobs` → `202` / `422`; `GET /jobs/{job_id}` → `200` / `404`; `GET /jobs?status=` → `200` / `422`.

Rules:

* `run_job` is the default processor. `word_count` → the number of
  whitespace-separated words in `text` (an int). `sum` → the sum of
  `numbers`. If the input is missing or the wrong type (e.g. `text` isn't a
  string, `numbers` isn't a list of numbers), raise `ValueError`.
* `create_app` uses `process` if given, else `run_job`. A worker calls
  `process(payload)` with the **whole posted object** (including `kind`).
* Start exactly `workers` worker threads in the app's **lifespan** startup
  and stop them on shutdown: jobs already running finish, then the threads
  exit and are joined. (Queued jobs that never started may be dropped.)
* A worker marks a job `running` **before** calling `process`; then `done`
  with `result` = the return value, or `failed` with `error` = `str(exc)`
  (or the exception's class name if that is empty). A failing job never
  kills its worker.
* `storage_dir` is for the follow-up (persisting jobs); jobs live in memory
  here and the tests pass `None`. No module-level state.

## Example

```
POST /jobs {"kind": "sum", "numbers": [1, 2, 3.5]}  → 202 {"job_id": "9f…", "status": "queued"}
GET  /jobs/9f…  (after polling)                      → 200 {"job_id": "9f…", "kind": "sum", "status": "done", "result": 6.5, "error": null}
POST /jobs {"kind": "nope"}                          → 422
```

## Constraints

* The job table is shared by the request threads and the workers: guard it
  with a `threading.Lock` and hand out copies, not live dicts.
* `POST` must never wait for the job: the tests inject a `process` that
  blocks until they release it.

<details><summary>Hint 1</summary>

Write an `@asynccontextmanager` lifespan and pass it as `FastAPI(lifespan=...)`.
Before its `yield`, start the worker threads; after it, put one `None` sentinel
per worker on the queue and `join()` every thread.
</details>

<details><summary>Hint 2</summary>

The worker loop: `job_id = q.get()`; `None` means stop. Set `running` under
the lock, call `process` **outside** the lock (it's slow), then set the
outcome under the lock. Wrap only the `process` call in `try/except Exception`.
</details>

## Follow-up (talk it through)

* The process restarts with 50 jobs queued. How would `storage_dir` make jobs
  durable, and what do you do with jobs that were `running` at crash time?
* Threads vs processes vs a real queue (Redis/SQS + Celery-style workers):
  what decides it? What about CPU-bound jobs and the GIL?
* A client polls every 10 ms. How do you push back (Retry-After, long polling, webhooks)?
