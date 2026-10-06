# Tasks API v1

Base URL: given to you (in tests, an `httpx.Client` already pointing at it).
All bodies are JSON. Timestamps are ISO-8601 UTC, e.g. `2024-04-02T10:15:00Z`
(but see "Data quality").

## Authentication

Send your API key in the `X-API-Key` header on every `/v1` request:

```
GET /v1/projects/prj_01/tasks
X-API-Key: key_live_...
```

A missing or wrong key returns `401 {"error": "missing_api_key" | "invalid_api_key"}`.
Keys do not expire.

## Tasks of a project

```
GET /v1/projects/{project_id}/tasks?limit=25&cursor=<opaque>
```

Cursor-paginated, in a stable order (by task id). `limit` is 1–25 (default 10).
Pass the previous response's `next_cursor` to get the next page; `next_cursor`
is `null` on the last page. Cursors are opaque: do not build or modify them.
Optional filters: `status`, `is_gold`.
Returns `404 {"error": "not_found"}` if the project does not exist.

```json
{
  "data": [
    {
      "id": "tsk_0015",
      "project_id": "prj_01",
      "status": "completed",
      "priority": 5,
      "is_gold": false,
      "gold_label": null,
      "payload": {"text": "Sample sentence 15 for review."},
      "tags": ["urban"],
      "reward_cents": 20,
      "created_at": "2024-04-02T06:03:50Z",
      "completed_at": "2024-04-02T07:07:50Z",
      "updated_at": "2024-04-02T07:07:50Z"
    }
  ],
  "next_cursor": "eyJyIjogInRhc2tzIi..."
}
```

Image tasks have `payload: {"image_url": "...", "dimensions": {"width": 1920, "height": 720}}`.
`status` is one of `pending`, `in_progress`, `completed`, `rejected`.

`GET /v1/projects/{project_id}` returns the project itself (or `404`).

## Rate limits

Each API key may send a fixed number of requests per sliding window. Every
`/v1` response (successes, errors and 429s alike) carries:

| header | meaning |
|---|---|
| `X-RateLimit-Limit` | requests allowed per window |
| `X-RateLimit-Remaining` | requests you may still send in the current window |
| `X-RateLimit-Reset` | Unix time (seconds) at which a request slot frees up again |

Going over the limit returns `429 {"error": "rate_limited"}` with a
`Retry-After` header giving the number of seconds to wait (`Retry-After: 8`).
Every response also has a standard `Date` header.

## Errors

| status | meaning | body |
|---|---|---|
| 400 | bad parameter (`limit`, `cursor`) | `{"error": "..."}` |
| 401 | missing or invalid API key | `{"error": "..."}` |
| 404 | unknown project | `{"error": "not_found"}` |
| 429 | rate limited; see above | `{"error": "rate_limited"}` |
| 500, 502, 503, 504 | transient upstream failure; safe to retry | `{"error": "upstream_error"}` |

The platform is under heavy load. Expect, besides 5xx responses:

* **slow responses**: some requests hang until your HTTP timeout fires;
* **truncated bodies**: a `200` whose body is cut off mid-JSON. Like a 5xx,
  this is transient: the same request usually succeeds when sent again.

All `GET`s are safe to retry.

## Data quality

The task records come from several generations of the platform and are not
consistently typed on the wire: `priority` or `reward_cents` may be a numeric
string (`"2"`), `reward_cents` may be `null`, `tags` may be a comma-separated
string or missing, `created_at` may be an epoch number or lack its `Z`,
`status` may be upper-case or padded with spaces, `payload.dimensions` may be
missing. Downstream loaders handle that; an export should hand over each
record exactly as the API returned it.

Example raw responses are in `data/recorded/`.
