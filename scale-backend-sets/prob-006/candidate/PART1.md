# Part 1: Project throughput report (about 20 minutes)

Operations wants a daily report of how far each customer project has got.
The data lives in the Projects API (`API.md`). Write a client for it and a
function that builds the report.

## Contract (keep these signatures; tests call them)

```python
from report.client import ApiClient, ApiError, AuthError
from report.report import build_report

client = ApiClient(http, client_id, client_secret, clock)  # http: httpx.Client with base_url set
report = build_report(client)                               # returns a dict (below)
```

* `ApiClient` must send every request through the given `http` client, so tests
  can point it at the mock. Use `clock` for any time you need.
* `python -m report --base-url ... --out report.json` is already wired up in
  `report/__main__.py`; it calls `build_report` and writes the result.

## Fetching

* Get a token from `POST /oauth/token` with the client credentials and send it
  as a bearer token on every `/v1` request.
* Read **every** project (all statuses) from `GET /v1/projects`, following the
  page numbers until `total_pages`.
* Read every task of each project from `GET /v1/projects/{id}/tasks`,
  following `next_cursor` until it is `null`.
* In this part, any `/v1` response that is not 2xx raises `ApiError` (it should
  carry the status code and the path), and a non-200 token response raises
  `AuthError`. Retrying comes later.

## The report

```json
{
  "generated_at": "2024-05-01T08:00:00Z",
  "projects": [
    {
      "project_id": "prj_01",
      "name": "Acme lidar cuboid 1",
      "customer_id": "cus_01",
      "status": "active",
      "tasks_total": 51,
      "tasks_completed": 27,
      "completion_rate": 0.5294,
      "median_minutes_to_complete": 312.5
    }
  ],
  "totals": {"projects": 12, "tasks_total": 600, "tasks_completed": 291}
}
```

* `generated_at`: the clock's time when `build_report` starts, ISO-8601 UTC.
* `projects`: one entry per project, sorted by `project_id`.
* `completion_rate`: `tasks_completed / tasks_total` rounded with `round(x, 4)`;
  `null` when the project has no tasks.
* `median_minutes_to_complete`: the median (as `statistics.median` defines it)
  of `completed_at - created_at` in minutes over the project's completed tasks,
  computed on the unrounded values and then `round(x, 1)`; `null` when there are
  no completed tasks.
* `totals` sums over all projects.

Write tests against `mock_services.api.make_api()` (see its docstring). They
should not depend on the exact numbers of one seed.
