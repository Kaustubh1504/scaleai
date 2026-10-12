# 17. Crawl linked resources with BFS

Access reviews need "every team under Acme": the org chart is a tree of orgs,
each owning some teams. The **Org API** only gives you one org at a time with
links to its children. The data is years old and messy: some orgs list a
child twice, two orgs share a child, one child even lists an **ancestor** as
its child (a cycle), and a few children were deleted and now 404.

## The API

`GET /v1/orgs/{org_id}`:

```json
{"id": "org_eng", "name": "Eng", "parent": "org_acme",
 "children": ["org_ml", "org_platform"], "team_ids": ["t_backend", "t_frontend"]}
```

or **404** if the org doesn't exist. `parent` is an id or `null`.

## Setup

```python
from problem_api import make_api
api = make_api(); client = api.client()      # the messy Acme org chart
```

`make_api(orgs)` accepts your own `{org_id: org}` graph (build orgs with
`problem_api.org(id, parent, children, team_ids)`) if you want a tiny case.
The `if __name__ == "__main__":` block is what the Run button executes: fetch a
few orgs by hand there (`org_acme`, `org_ml`, `org_ghost`) and look at the links.

## Your task

Your module must define:

* `class ApiError(Exception)`: constructor `ApiError(status, path, message="")`;
  attributes `.status: int`, `.path: str`.
* `collect_teams(client: httpx.Client, root_id: str, max_depth: int | None = None) -> dict`,
  returning a dict with exactly three keys:
  * `"orgs_visited": int`: orgs successfully fetched, root included
  * `"team_ids": list[str]`: every team id seen, unique, sorted
  * `"missing_orgs": list[str]`: child ids that returned 404, unique, sorted

Rules:

* Start at `root_id` and follow **`children` only**. Never follow `parent`.
* Walk **breadth-first**. The root is depth 0, its children depth 1, and so
  on. An org's depth is its *shortest* distance from the root.
* Request each org id **at most once**, 404s included, however many orgs link
  to it.
* `max_depth`: never request an org deeper than `max_depth`. `None` means no limit.
* A 404 for a child: add it to `missing_orgs` and carry on.
* A 404 for the **root**: raise `ApiError(404, "/v1/orgs/<root_id>")`.
* Any other non-2xx raises `ApiError(status, path)`.

## Example

```python
collect_teams(client, "org_acme")
# {"orgs_visited": 7,
#  "team_ids": ["t_backend", "t_exec", "t_frontend", "t_infra", "t_ml", "t_ops", "t_research", "t_support"],
#  "missing_orgs": ["org_ghost", "org_vendor_gone"]}
# 9 requests (7 orgs + 2 that 404)

collect_teams(client, "org_acme", max_depth=1)
# {"orgs_visited": 3, "team_ids": ["t_backend", "t_exec", "t_frontend", "t_ops"], "missing_orgs": ["org_ghost"]}
```

## Constraints

* Go through HTTP only. Don't read `api.orgs` or `ORGS`.
* No recursion needed (or wanted): a real org chart can be deep.

<details><summary>Hint 1</summary>

A `collections.deque` of (org id, depth) pairs plus a `seen` set. Mark an id
as seen when you **queue** it, not when you pop it, or a child listed twice
gets fetched twice.
</details>

<details><summary>Hint 2</summary>

Why BFS and not DFS with a depth limit? Draw `root -> [a, b]`, `a -> [b]`,
`b -> [c]` with `max_depth=2` and walk it depth-first.
</details>

## Follow-up (talk it through)

* The chart has 50,000 orgs. How would you fetch a level concurrently, and
  what would you cap?
* Should a cycle in the data be silently skipped, logged, or an error? Who
  needs to know?
* The crawl takes 20 minutes and the chart changes meanwhile. What can go wrong?
