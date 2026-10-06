# Part 1: Task creation and idempotency (about 20 minutes)

Tenants create annotation tasks with `POST /tasks`. Their HTTP clients retry
when a request times out, so a retried request must not create a second task.
Keeping state in memory is fine for this part.

## Tenant header

Every `/tasks` endpoint requires the header `X-Tenant-Id`.

| situation | status |
|---|---|
| header missing or empty | 400 |
| tenant not in the config's `tenants` | 403 |

A tenant only ever sees its own tasks.

## `POST /tasks`

Optional header `Idempotency-Key`: 1 to 64 characters, each one of
`A-Z a-z 0-9 _ -`. Any other value (including an empty string) is **400**.

JSON body:

| field | rule |
|---|---|
| `project` | string, at least 1 character; stored as given |
| `payload` | JSON object (any content) |
| `priority` | JSON integer 0–9, optional, default `5`. Strings (`"3"`), floats (`3.0`) and booleans are invalid. |

Any other field, a body that is not a JSON object, or malformed JSON is
**422** (FastAPI's default validation response is fine).

### Order of checks

Apply the checks in this order; the first one that fails decides the response:

1. `X-Tenant-Id` missing/empty (400), then unknown (403)
2. `Idempotency-Key` format (400)
3. body validation (422)
4. idempotency (replay or 409, below)
5. create the task (201)

So a request with no tenant header and an invalid body is a 400.

### Success: **201**

```json
{
  "id": "<string, unique>",
  "tenant_id": "acme",
  "project": "lidar-3d",
  "payload": {"scene": "s-002"},
  "priority": 5,
  "created_at": "2023-11-14T22:13:20+00:00"
}
```

`created_at` is the app clock's `clock.time()` at creation, as an ISO-8601
string with a UTC offset (`+00:00` or `Z`). Tests parse it with
`datetime.fromisoformat(value.replace("Z", "+00:00"))`.

### Idempotency

A request is identified by **(tenant, `Idempotency-Key`)**. Requests without
the header are never deduplicated.

* **Same body**: two bodies are the same when they validate to the same values.
  JSON key order (at any depth), whitespace, and omitting `priority` versus
  sending `"priority": 5` do not matter.
* First request with a key: handled normally. If it creates a task (201), the
  key is recorded with the request body and the response. Requests that fail
  (any 4xx) are **not** recorded, so the client can retry them with the same key.
* Later request, same tenant, same key, same body: no new task. Respond with
  the recorded status (201) and exactly the recorded JSON body, plus the header
  `Idempotent-Replayed: true`. The original response does not carry that header.
* Later request, same tenant, same key, different body: **409**, no new task.
* Keys are scoped per tenant: the same key used by another tenant is unrelated.

## `GET /tasks/{task_id}`

**200** with the task (same JSON as the 201 body) if it belongs to the caller's
tenant; **404** if it does not exist or belongs to another tenant.

## `GET /tasks`

**200** with `{"tasks": [ ... ]}`: all of the caller's tasks, oldest first
(creation order). No pagination.

## Constraints

* Keep the `create_app(storage_dir, clock, tenants)` signature in `app/main.py`.
  Use the injected `clock` for all time; write files only under `storage_dir`.
* Write tests for your work.
