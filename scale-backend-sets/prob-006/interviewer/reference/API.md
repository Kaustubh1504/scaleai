# Projects API v1

Base URL: given to you (in tests, an `httpx.Client` already pointing at it).
All bodies are JSON. All timestamps are ISO-8601 UTC, e.g. `2024-04-02T10:15:00Z`.

## Authentication

```
POST /oauth/token
{"client_id": "client", "client_secret": "secret"}
```

```json
200 {"access_token": "tok_...", "token_type": "bearer", "expires_in": 300, "refresh_token": "rft_..."}
401 {"error": "invalid_client"}
```

Send `Authorization: Bearer <access_token>` on every `/v1` request. Tokens
expire `expires_in` seconds after they are issued. To get a new one without
re-sending the client secret:

```
POST /oauth/token
{"grant_type": "refresh_token", "refresh_token": "rft_..."}
```

Refresh tokens are single use; each successful token response contains a new
one. A used or unknown refresh token returns `400 {"error": "invalid_grant"}`.

Unauthenticated `/v1` requests return `401` with
`{"error": "missing_token" | "invalid_token" | "token_expired"}`.

## Projects

```
GET /v1/projects?page=1&per_page=10
```

Page-numbered. `page` starts at 1; `per_page` is 1–10 (default 10).
Filters: `status`, `customer.id`, `task_type`.

```json
{
  "results": [
    {
      "id": "prj_01",
      "name": "Acme lidar cuboid 1",
      "customer": {"id": "cus_01", "name": "Acme Robotics", "tier": "enterprise"},
      "status": "active",
      "task_type": "lidar_cuboid",
      "settings": {"redundancy": 3, "gold_ratio": 0.05, "labels": ["vehicle", "person", "animal"]},
      "created_at": "2024-03-11T00:59:00Z",
      "updated_at": "2024-03-29T00:59:00Z"
    }
  ],
  "page": 1, "per_page": 10, "total": 12, "total_pages": 2
}
```

`status` is one of `active`, `paused`, `archived`.
`GET /v1/projects/{id}` returns one project or `404 {"error": "not_found"}`.

## Tasks of a project

```
GET /v1/projects/{project_id}/tasks?limit=25&cursor=<opaque>
```

Cursor-paginated. `limit` is 1–25 (default 10). Pass the previous response's
`next_cursor` to get the next page; `next_cursor` is `null` on the last page.
Cursors are opaque: do not build or modify them. Filters: `status`, `is_gold`.
`404` if the project does not exist.

```json
{
  "data": [
    {
      "id": "tsk_0001",
      "project_id": "prj_02",
      "status": "completed",
      "priority": 5,
      "is_gold": false,
      "gold_label": null,
      "payload": {"image_url": "https://cdn.example.com/img/00001.jpg", "dimensions": {"width": 1920, "height": 720}},
      "tags": ["highway", "occluded"],
      "reward_cents": 8,
      "created_at": "2024-03-23T06:44:29Z",
      "completed_at": "2024-03-23T07:31:29Z",
      "updated_at": "2024-03-23T07:31:29Z"
    }
  ],
  "next_cursor": "eyJyIjogInRhc2tzIi..."
}
```

`status` is one of `pending`, `in_progress`, `completed`, `rejected`.
`completed_at` is set only for completed tasks, otherwise `null`.

## Errors

| status | meaning | body |
|---|---|---|
| 400 | bad parameter (page, per_page, limit, cursor) | `{"error": "..."}` |
| 401 | see Authentication | `{"error": "..."}` |
| 404 | unknown resource or id | `{"error": "not_found"}` |
| 429 | rate limited | `{"error": "rate_limited"}` + `Retry-After` header |
| 500, 502, 503 | transient upstream failure; safe to retry | `{"error": "upstream_error"}` |

`Retry-After` is either a number of seconds (`Retry-After: 7`) or an HTTP date
(`Retry-After: Tue, 05 Mar 2024 10:00:07 GMT`). Every response has a `Date`
header; compare an HTTP-date `Retry-After` against it, not against your own clock.
Rate-limited responses also carry `X-RateLimit-Limit`, `X-RateLimit-Remaining`
and `X-RateLimit-Reset`.

Under load the API occasionally answers slowly or returns a `200` whose body is
cut off (invalid JSON). Both are transient.
