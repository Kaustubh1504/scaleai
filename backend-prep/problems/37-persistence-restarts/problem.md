# 37. A task store that survives restarts

The labelling pipeline creates review tasks by calling a small internal
service. Today it keeps tasks in a Python dict, so every deploy wipes them.
Worse, the pipeline **retries** a create when it times out, so a create can
arrive twice. Make the service durable and make creates safe to retry.

## The API you build

A task is `{"id": str, "title": str, "assignee": str | null, "status": "open" | "done"}`.

| method | path | body | success |
|---|---|---|---|
| `POST` | `/tasks` | `{"id", "title", "assignee"?}` | `201` + task (`status` starts `"open"`, `assignee` defaults to `null`) |
| `GET` | `/tasks/{id}` | | `200` + task, or `404` |
| `GET` | `/tasks` | | `200` + `{"tasks": [...]}` in **creation order** |
| `PUT` | `/tasks/{id}` | `{"title", "assignee"?, "status"?}` | `200` + updated task, or `404` |

* The client chooses `id`. It must match `^[A-Za-z0-9_-]{1,64}$`; `title` must
  be a non-empty string; `status` must be `"open"` or `"done"`. Anything else
  is FastAPI's `422` (pydantic models do this for you). Unknown keys are ignored.
* `PUT` is a full replace of the mutable fields: a missing `assignee` means
  `null`, a missing `status` means `"open"`. It does not change the task's
  position in the list.

## Setup

```python
c = TestClient(create_app(tmp_path))    # how the tests build your app
c = TestClient(create_app(tmp_path))    # calling it again over the same dir is a "restart"
```

Your file starts empty. An `if __name__ == "__main__":` block is what the Run
button executes: use it to create, retry, restart and look at the files.

## Your task

Write in your file:

* `create_app(storage_dir: str | Path) -> FastAPI`: a factory serving the four routes in the table above (plus `409` below).

Pydantic request models are the easy way to get the `422`s; their names are up to you.

* **Durable.** Store state under `storage_dir` (create it, including parents,
  if missing). Your choice: a JSON file or SQLite (`sqlite3` is in the
  standard library). Once a request has returned, an app created later with
  `create_app(same_dir)` must see exactly that state, including list order.
* **Atomic.** A crash mid-write must never leave a half-written store. If you
  write through a temporary file, give it a `.tmp` suffix: no `*.tmp` file may
  remain after a request returns.
* **Idempotent create.** `POST` with an `id` that already exists:
  * if the stored task's current `title` and `assignee` equal the request's
    (a missing `assignee` counts as `null`) → `200` with the stored task,
    unchanged. This is a retry.
  * otherwise → `409` (`{"detail": ...}`), and nothing changes.
* Two different `storage_dir`s are completely independent. No module-level state.

## Example

```python
c = TestClient(create_app(tmp))
c.post("/tasks", json={"id": "t1", "title": "Review batch 7"})   # 201 {"id": "t1", "title": "Review batch 7", "assignee": null, "status": "open"}
c.post("/tasks", json={"id": "t1", "title": "Review batch 7"})   # 200, same task (a retry)
c.post("/tasks", json={"id": "t1", "title": "Something else"})   # 409
c.put("/tasks/t1", json={"title": "Review batch 7", "status": "done"})  # 200, status done

c2 = TestClient(create_app(tmp))                                 # "restart"
c2.get("/tasks").json()   # {"tasks": [{"id": "t1", ..., "status": "done"}]}
```

## Constraints

* Persist on every write; don't rely on a shutdown hook (a crash doesn't run one).
* Keep it readable: a small storage layer (load / save, or a few SQL
  statements) and thin route handlers.

<details><summary>Hint 1</summary>

JSON route: keep a `dict[str, dict]` (dicts remember insertion order) and save
the whole thing as a list. Write to `tasks.json.tmp`, `flush()` +
`os.fsync()`, then `os.replace(tmp, final)`: the rename is atomic, so readers
see the old file or the new one, never half of each.
</details>

<details><summary>Hint 2</summary>

SQLite route: give the table an autoincrementing `seq` column next to a unique
`id`, and list with `ORDER BY seq`. Each write in
`with conn:` is a transaction. Open a connection per request (or use
`check_same_thread=False` and a lock): FastAPI runs `def` handlers in a thread pool.
</details>

<details><summary>Hint 3</summary>

To return 201 vs 200 from one route, take a `response: Response` parameter
and set `response.status_code`, or return a `JSONResponse(status_code=...)`.
</details>

## Follow-up (talk it through)

* Two replicas of this service share the directory. What breaks with the JSON
  file approach? With SQLite? What would you use instead?
* Comparing the body works for creates. How do idempotency keys
  (`Idempotency-Key` header) generalise it to any POST, and how long do you keep them?
* Rewriting the whole JSON file is O(n) per write. When does that start to hurt, and what's the fix?
