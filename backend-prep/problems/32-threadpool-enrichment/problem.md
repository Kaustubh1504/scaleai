# 32. Thread pool enrichment

The labeling dashboard shows a table of 200 task ids, and product wants each
row enriched with the task's status, project and annotator. The Tasks API only
has a **single-task** endpoint, and each call takes ~20 ms. Fetching 200 tasks
one by one takes ~4 s; your job is to fetch them **concurrently with threads**
while capping how hard you hit the API.

## The API

`GET /v1/tasks/{task_id}` → `200`

```json
{"id": "task_0007", "project_id": "proj_beta", "status": "completed",
 "annotator_id": "ann_10", "label_count": 8}
```

* Unknown id → **404** `{"error": "task task_9999 not found"}`.
* Latency varies per task, so responses finish **out of order**.

## Setup

```python
from problem_api import make_api
api = make_api(n_tasks=200)    # task_0001 .. task_0200 exist
client = api.client()          # httpx.Client wired to the mock; paths like "/v1/tasks/task_0007"
```

Tests check `api.max_in_flight` to see how many requests overlapped. The
`if __name__ == "__main__":` block is what the Run button executes: fetch one
task and a 404 there, and time 20 serial requests.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, task_id, message="")`;
  attributes `.status: int` (HTTP status) and `.task_id: str` (the id that failed).
* `enrich(client: httpx.Client, task_ids: list[str], max_workers: int = 8) -> list[dict]`

* Return one record (the JSON body) per input id, **in input order**,
  regardless of which response finished first.
* Use a `concurrent.futures.ThreadPoolExecutor`. Never have more than
  `max_workers` requests in flight at once, and do run them in parallel.
* If `task_ids` has duplicates, fetch each distinct id **once**; the output
  still has one entry per input position.
* `[]` returns `[]` without making any request.
* `max_workers < 1` raises `ValueError`.
* Any non-2xx response raises `ApiError` with `.status` and `.task_id`.
* Share the one `client` across threads: `httpx.Client` is thread-safe (its
  connection pool is locked), so don't create a client per request.

## Example

```python
api = make_api(n_tasks=200)
enrich(api.client(), ["task_0003", "task_0001", "task_0003"], max_workers=4)
# 2 requests (task_0003 once), result:
# [{"id": "task_0003", ...}, {"id": "task_0001", ...}, {"id": "task_0003", ...}]
```

## Constraints

* Go through HTTP only (don't read `api.tasks`).
* No `asyncio` here; that's problem 33.

<details><summary>Hint 1</summary>

Run a one-id fetch function over the unique ids with `ThreadPoolExecutor.map`.
`map` yields results **in the order of its
input**, not completion order, and re-raises a worker's exception when you
reach that result.
</details>

<details><summary>Hint 2</summary>

Dedupe while keeping order with `dict.fromkeys(task_ids)`, build an
`{id: record}` map, then look each input position up in it.
</details>

## Follow-up (talk it through)

* Why do threads help here despite the GIL? When would they not?
* `pool.map` vs `submit` + `as_completed`: when would you pick each?
* One task 404s while 50 others are in flight. What happens to them, and how
  would you cancel the rest early (`pool.shutdown(cancel_futures=True)`)?
