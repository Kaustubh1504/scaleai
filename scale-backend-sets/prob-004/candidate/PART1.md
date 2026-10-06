# Part 1: Leases (about 20 minutes)

Today `POST /tasks/claim` hands the same task to everyone who asks, and anyone
can submit any task. Annotators are duplicating each other's work. Replace this
with **leases**: claiming a task reserves it for one annotator for a limited
time.

Read `app/` first. Keep the `create_app(storage_dir, clock, lease_seconds, redundancy)`
signature; in this part `redundancy` is always 1.

## Time

All timestamps (`created_at`, `expires_at`, `lease_expires_at`, `submitted_at`)
are unix seconds from the **app's injected clock** (`clock.time()`). The tests
pass a `FakeClock` and move time with `clock.advance(seconds)`.

A lease is **live** while `clock.time() < expires_at`. At `expires_at` it is
expired, exactly as if it never existed.

## States

| state | meaning |
|---|---|
| `pending` | nobody holds a live lease and it has not been submitted |
| `leased` | an annotator holds a live lease |
| `submitted` | the lease holder submitted a label (final) |

When a lease expires the task is `pending` again. This must be visible
everywhere, including `GET /tasks/{id}` and `GET /tasks?state=`, even if
nobody has called `claim` since.

## The task object

Every endpoint that returns a task returns the existing shape plus `leases`,
the list of **live** leases (with redundancy 1, at most one):

```json
{"id": "t1", "data": {}, "labels": ["a", "b"], "state": "leased", "created_at": 1700000000.0,
 "leases": [{"annotator_id": "alice", "expires_at": 1700000060.0}],
 "submissions": []}
```

## The `X-Annotator-Id` header

`claim`, `extend` and `submit` require it. If it is missing, empty or only
whitespace, respond **400** (this check comes before every other check).
Surrounding whitespace is stripped.

## `POST /tasks/claim`

* If the caller already holds a live lease, respond **200** with that same task
  and its lease **unchanged** (claiming again does not extend it, and does not
  give the caller a second task).
* Otherwise lease the **oldest claimable task by creation order** (batch order
  within a batch) to the caller, with `expires_at = now + lease_seconds`.
  A task is claimable if it is `pending` (a task whose lease expired is pending).
* **200** with the task object plus `"lease_expires_at": <expires_at>`.
* **204** with an empty body if nothing is claimable.

## `POST /tasks/{id}/extend`

The caller must hold a live lease on the task. Sets `expires_at = now + lease_seconds`.
**200** with the task object plus `lease_expires_at`.

## `POST /tasks/{id}/submit`

Body `{"label": "<string>"}`. Checks, in this order:

1. unknown task: **404**
2. the caller does not hold a live lease on this task (never claimed, someone
   else's lease, the caller's lease expired, or already submitted): **409**
3. `label` is not one of the task's `labels`: **422** (the lease is kept)

On success the lease ends, the submission
`{"annotator_id", "label", "submitted_at"}` is recorded, the task becomes
`submitted`, and the response is **200** with the task object.

## Errors

| situation | status |
|---|---|
| missing / blank `X-Annotator-Id` | 400 |
| unknown task id (`extend`, `submit`, `GET`) | 404 |
| `extend` or `submit` without a live lease held by the caller | 409 |
| label not allowed | 422 |

409 and 404 bodies use FastAPI's `{"detail": "..."}` with a message that says
what is wrong (for example `"task t1 is leased by another annotator"`).

## Constraints

* Everything is stored in SQLite under `storage_dir` (no in-memory state that
  matters).
* `POST /tasks`, `GET /tasks/{id}` and `GET /tasks` keep working as they do today.
* Write tests for your work.
