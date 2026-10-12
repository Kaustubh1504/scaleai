# 04. Create a project (POST + error mapping)

Customer success creates labeling projects from a CLI. Right now any failure
prints `422 Unprocessable Entity` and nothing else, so people guess what was
wrong with their input. Write the client function that creates a project and
turns every failure into an exception the CLI can explain.

## The API

`POST /v1/projects` with header `Authorization: Bearer <token>` and a **JSON** body:

```json
{"name": "Retail shelf boxes", "description": "optional, <= 500 chars", "tags": ["vision", "retail"]}
```

`name` is required (1–80 chars). `description` and `tags` (each tag 1–20
chars, at most 10) are optional. Responses:

```
201 {"id": "prj_003", "name": "Retail shelf boxes", "description": null, "tags": [...], "status": "active", ...}
401 {"detail": "Not authenticated"}
409 {"detail": "a project named 'Support chat RLHF' already exists", "existing_id": "prj_002"}
415 {"detail": "Unsupported Media Type: expected application/json, got application/x-www-form-urlencoded"}
422 {"detail": [{"loc": ["body", "name"], "msg": "String should have at least 1 character", "type": "string_too_short"},
                {"loc": ["body", "tags", 1], "msg": "String should have at most 20 characters", "type": "string_too_long"}]}
```

The 422 shape is what FastAPI produces: `loc` is the path to the bad value,
starting with where it came from (`"body"`, `"query"`, ...).

## Setup

```python
from problem_api import make_api, TOKEN
client = make_api().client()   # httpx.Client for the mock Projects API; TOKEN is a valid bearer token
```

The `if __name__ == "__main__":` block is what the Run button executes: use
it to POST a valid body, an invalid one, a duplicate name and a form body,
and print the raw status + JSON of each.

## Your task

Your module must define:

* `class ProjectApiError(Exception)`: `ProjectApiError(status, message="")`; attribute `.status: int`.
* `class AuthError(ProjectApiError)`: `AuthError(message="...")`; `.status == 401`.
* `class ValidationFailed(ProjectApiError)`: `ValidationFailed(errors)`; `.status == 422`, `.errors: list[dict]`.
* `class AlreadyExists(ProjectApiError)`: `AlreadyExists(existing_id, message="")`; `.status == 409`, `.existing_id: str`.
* `create_project(client: httpx.Client, token: str, name: str, *, description: str | None = None, tags: list[str] | None = None) -> dict`

Rules:

* Send `Authorization: Bearer <token>`.
* Send the body with **`json=`**. Include `description` / `tags` only when they are not `None`.
* **201**: return the created project (the parsed body).
* **401**: raise `AuthError`.
* **409**: raise `AlreadyExists` with `existing_id` from the body.
* **422**: raise `ValidationFailed` whose `errors` is one
  `{"field": ..., "message": ...}` per entry in `detail`, **in the same order**.
  `field` is `loc` with a leading `"body"` dropped and the rest joined by
  `"."` (`["body", "tags", 1]` -> `"tags.1"`; `["body"]` -> `""`).
  `message` is `msg`.
* Any other non-2xx (415, 500, ...): raise `ProjectApiError(status)` itself, not a subclass.

## Example

```python
create_project(client, TOKEN, "Retail shelf boxes", tags=["vision"])
# {"id": "prj_003", "name": "Retail shelf boxes", "description": None, "tags": ["vision"], ...}

create_project(client, TOKEN, "", tags=["ok", "this-tag-is-way-too-long"])
# ValidationFailed: errors == [{"field": "name", "message": "String should have at least 1 character"},
#                              {"field": "tags.1", "message": "String should have at most 20 characters"}]
```

## Constraints

* Go through HTTP only. Don't validate the input yourself: the server is the
  source of truth for the rules, your job is to report them well.

<details><summary>Hint 1</summary>

`client.post(url, data={...})` sends a **form** body
(`application/x-www-form-urlencoded`); `client.post(url, json={...})`
serialises to JSON and sets `Content-Type: application/json`. APIs that
expect JSON answer the first with 415 (or a confusing 422).
</details>

<details><summary>Hint 2</summary>

Map status codes to exceptions in one place, after the request: check `201`,
then `401`, `409`, `422`, then a catch-all `if not resp.is_success`.
`".".join(str(p) for p in loc[1:])` handles integer indexes in `loc`.
</details>

## Follow-up (talk it through)

* The POST timed out. Did the project get created? How would an
  `Idempotency-Key` header let you retry safely?
* Why is it useful that `AuthError`, `ValidationFailed` and `AlreadyExists`
  share a base class?
* 409 vs 422: what's the difference, and which one could succeed later
  without changing the request?
