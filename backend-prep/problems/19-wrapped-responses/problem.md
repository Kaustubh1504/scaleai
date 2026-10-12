# 19. Unwrapping inconsistent envelopes

The workforce service was built by three teams, and each one wrapped its list
responses differently. Before you can do anything with annotators, reviewers
and leads, you need a single `unwrap()` that turns any of the known envelopes
into a plain `list[dict]`, and that fails **loudly** on a shape nobody has seen
before (silently returning `[]` is how a whole team disappears from payroll).

## The API

| endpoint | response body |
|----------|---------------|
| `GET /v1/annotators` | `{"data": [{"id": "w_004", "name": "Priya Raman", "locale": "en-IN"}, ...], "meta": {"count": 3}}` |
| `GET /v1/reviewers`  | `{"results": {"items": [{"id": "w_006", "name": "Sam Okafor", "queue": "rlhf"}, ...], "count": 2}}` |
| `GET /v1/leads`      | a bare list `[{"id": "w_005", "name": "Jonas Berg", "team": "vision"}, ...]` |

On some days `/v1/leads` returns `{"data": {...one lead...}}` or `{"items": []}`
instead. No auth, no pagination.

## Setup

```python
from problem_api import make_api
client = make_api().client()                          # the normal day
make_api(leads_shape="single").client()               # also "empty"; reviewers_shape="bad"
```

The `if __name__ == "__main__":` block is what the Run button executes: print
each endpoint's raw `resp.json()` there to see the three envelopes.

## Your task

Your module must define:

* `class UnexpectedShape(Exception)`: constructor `UnexpectedShape(keys)`;
  attribute `.keys: list[str]` (sorted top-level keys of the body; `[]` if it wasn't a dict).
* `class ApiError(Exception)`: constructor `ApiError(status, path, message="")`;
  attributes `.status: int`, `.path: str`.
* `unwrap(body) -> list[dict]`
* `fetch_everything(client: httpx.Client) -> list[dict]`

**`unwrap(body)`**:

* A **list** → returned as a list.
* A **dict** → look for the first of `"data"`, `"results"`, `"items"` that is
  present (in that order), and take its value `v`:
  * `v` is a list → `v`.
  * `v` is a dict containing `"items"` or `"results"` whose value is a list →
    that list (`items` checked first).
  * `v` is any other dict → it's a single record: `[v]`.
  * `v` is `None` → `[]`.
  * anything else → `UnexpectedShape`.
* A dict with none of those keys, or a body that is neither list nor dict →
  raise `UnexpectedShape(keys)` where `keys` is the **sorted** list of the
  body's top-level keys (`[]` for a non-dict).

**`fetch_everything(client)`**:

* `GET` each of the three endpoints **once**. A non-2xx response raises
  `ApiError(status, path)`.
* Returns one list of `{"id", "name", "role"}` dicts (drop every other field)
  where `role` is `"annotator"`, `"reviewer"` or `"lead"` by endpoint.
* Sorted by `id` ascending. Let `UnexpectedShape` propagate.

## Example

```python
unwrap({"data": {"items": [{"id": 1}], "next": None}})   # [{"id": 1}]
unwrap({"data": {"id": 9, "name": "solo"}})              # [{"id": 9, "name": "solo"}]
unwrap({"payload": [], "ok": True})                       # raises UnexpectedShape(["ok", "payload"])

fetch_everything(make_api().client())
# [{"id": "w_001", "name": "Diego Alvarez", "role": "annotator"},
#  {"id": "w_002", "name": "Ana Silva", "role": "reviewer"}, ...]   (7 people)
```

## Constraints

* Go through HTTP only; don't import the sample lists from `problem_api`.
* `unwrap` doesn't make requests; it only looks at an already-parsed body.

<details><summary>Hint 1</summary>

`next((k for k in ("data", "results", "items") if k in body), None)` finds the
envelope key. Then branch on `isinstance(v, list)` / `isinstance(v, dict)`.
</details>

<details><summary>Hint 2</summary>

Keep the endpoint → role mapping in a small dict and loop over it; the three
fetches are identical except for the path.
</details>

## Follow-up (talk it through)

* Why raise on an unknown envelope instead of returning `[]`? When would
  you rather log and continue?
* `{"data": {...}}` could be a single record *or* an envelope you don't know
  yet. How would you make that guess safer (e.g. require an `id`)?
* How would you get the three teams to converge on one envelope without
  breaking existing clients?
