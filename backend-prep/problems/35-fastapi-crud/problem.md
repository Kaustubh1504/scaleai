# 35. FastAPI CRUD: Projects

Customers on the labeling platform group their work into **projects**. You're
building the first version of the Projects service: an in-memory FastAPI app
with proper validation and status codes. The storage will be swapped for
Postgres later, so keep the HTTP layer clean.

## Setup

```python
from fastapi.testclient import TestClient
client = TestClient(create_app())     # tests pass create_app(clock=FakeClock())
```

`kit.RealClock` and `kit.FakeClock` both have `.time()`. The
`if __name__ == "__main__":` block is what the Run button executes: drive your
app with `TestClient` there and print each status and body.

## Your task

Your module must define:

* `create_app(clock=None) -> fastapi.FastAPI`, serving the five routes below.

Every call returns a **new app with its own empty store** (no module-level
state). `clock` has `.time()` (unix seconds); default to `kit.RealClock()`.

### Project shape

```json
{"id": 1, "name": "Street signs", "priority": 3, "tags": ["vision"],
 "created_at": "2023-11-14T22:13:20+00:00"}
```

* `id`: int, assigned 1, 2, 3, ... and **never reused** after a delete.
* `created_at`: `datetime.fromtimestamp(clock.time(), timezone.utc).isoformat()`.

### Input rules (violations → FastAPI's default **422**)

* `name`: string, **whitespace-stripped**, then 1..100 chars.
* `priority`: int 1..5, default 3.
* `tags`: list of strings, at most 10, default `[]`.

### Endpoints

| method & path | success | errors |
|---|---|---|
| `POST /projects` | **201** + project | 422; **409** if the name is taken (case-insensitive, after strip) |
| `GET /projects/{id}` | 200 + project | **404** |
| `GET /projects?limit=20&offset=0&tag=` | 200 `{"items": [...], "total": N}` | 422 if `limit` not in 1..100 or `offset` < 0 |
| `PATCH /projects/{id}` | 200 + updated project | 404, 422, 409 (name taken by **another** project) |
| `DELETE /projects/{id}` | **204**, empty body | 404 |

* Error bodies are `{"detail": "<message>"}` (raise `HTTPException`).
* List: sorted by `id` ascending; `tag` (optional) keeps projects whose
  `tags` contain it exactly; `total` is the count **after** filtering, before
  `limit`/`offset`.
* PATCH updates **only the fields present** in the body (same rules as
  create); fields you leave out keep their value. `id` and `created_at` never
  change. Renaming a project to its own name in different case is allowed.

## Example

```python
client = TestClient(create_app())
client.post("/projects", json={"name": "  Street signs ", "tags": ["vision"]})
# 201 {"id": 1, "name": "Street signs", "priority": 3, "tags": ["vision"], "created_at": "..."}
client.post("/projects", json={"name": "STREET SIGNS"})          # 409
client.patch("/projects/1", json={"priority": 5})                # 200, name/tags unchanged
client.get("/projects", params={"limit": 0})                     # 422
```

## Constraints

* Use pydantic models for the request bodies; let FastAPI produce the 422s.
* Tests use `fastapi.testclient.TestClient`; no real server.

<details><summary>Hint 1</summary>

Put the rules on a pydantic body model: `Annotated[str, StringConstraints(...)]`
strips and length-checks `name`, `Field(ge=, le=, max_length=)` covers priority
and tags. Query params validate the same way: `limit: int = Query(20, ge=1, le=100)`.
</details>

<details><summary>Hint 2</summary>

For PATCH, make every field optional in a separate model and use
`body.model_dump(exclude_unset=True)`: it contains only the keys the client
actually sent. Put the store in a dict **inside** `create_app` so each app
gets its own.
</details>

## Follow-up (talk it through)

* Two requests create the same name at the same time. With Postgres, how do
  you make the 409 race-free?
* Offset pagination vs cursors for this list endpoint once there are 10M
  projects?
* PUT vs PATCH: what would a client expect from each?
