# Contributor Platform API v1

Base URL: given to you (in tests, an `httpx.Client` already pointing at it).
All bodies are JSON. Canonical timestamps are ISO-8601 UTC, e.g. `2024-04-02T10:15:00Z`
(but see [Data quality](#data-quality)).

The API grew over several years, so collections paginate differently and use
different envelopes. Read each section.

## Authentication

```
POST /oauth/token
{"client_id": "...", "client_secret": "..."}
```

```json
200 {"access_token": "tok_...", "token_type": "bearer", "expires_in": 300, "refresh_token": "rft_..."}
401 {"error": "invalid_client"}
```

Send `Authorization: Bearer <access_token>` on every `/v1` request. Tokens expire
`expires_in` seconds after they are issued. (A refresh grant exists:
`{"grant_type": "refresh_token", "refresh_token": "rft_..."}`; refresh tokens are single use.)

Unauthenticated `/v1` requests return `401` with
`{"error": "missing_token" | "invalid_token" | "token_expired"}`.

## Pagination at a glance

| collection | style | parameters | envelope | stop when |
|---|---|---|---|---|
| `/v1/annotators` | offset | `offset` (from 0), `limit` 1–20 (default 10) | `items, offset, limit, total` | `offset + len(items) >= total` |
| `/v1/tasks` | cursor | `cursor`, `limit` 1–100 (default 25) | `data, next_cursor` | `next_cursor` is `null` |
| `/v1/submissions` | cursor | `cursor`, `limit` 1–100 (default 50) | `data, next_cursor` | `next_cursor` is `null` |
| `/v1/reviews` | page | `page` (from 1), `per_page` 1–50 (default 20) | `results, page, per_page, total, total_pages` | `page >= total_pages` |
| `/v1/results` | page | `page`, `per_page` 1–50 (default 20) | `results, page, per_page, total, total_pages` | `page >= total_pages` |

Cursors are opaque: pass back the previous response's `next_cursor` unchanged.
An out-of-range `limit`/`per_page`/`offset`/`page` or a bad cursor returns `400`.
Every collection is returned in `id` order. All list endpoints accept
`?updated_since=<ISO-8601>` and the filters listed below (`?field=value`).
`GET /v1/<collection>/{id}` returns one record or `404 {"error": "not_found"}`.

## Annotators

```
GET /v1/annotators?offset=0&limit=20
```

Filters: `country`, `level`, `is_active`.

```json
{
  "items": [
    {
      "id": "ann_001",
      "handle": "annotator001",
      "country": "PH",
      "level": 3,
      "hourly_rate_cents": 600,
      "skills": ["image_bbox", "lidar_cuboid"],
      "is_active": true,
      "joined_at": "2023-07-14T00:00:00Z",
      "updated_at": "2023-07-20T00:00:00Z"
    }
  ],
  "offset": 0, "limit": 20, "total": 30
}
```

`is_active` is `false` for contributors whose account is suspended or under review.

## Tasks

```
GET /v1/tasks?limit=100&cursor=<opaque>
```

Filters: `project_id`, `status`, `is_gold`.

```json
{
  "data": [
    {
      "id": "tsk_0001",
      "project_id": "prj_02",
      "status": "completed",
      "priority": 5,
      "is_gold": true,
      "gold_label": "car",
      "payload": {"image_url": "https://cdn.example.com/img/00001.jpg", "dimensions": {"width": 1920, "height": 720}},
      "tags": ["highway", "occluded"],
      "reward_cents": 12,
      "created_at": "2024-03-23T06:44:29Z",
      "completed_at": "2024-03-23T07:31:29Z",
      "updated_at": "2024-03-23T07:31:29Z"
    }
  ],
  "next_cursor": "eyJyIjogInRhc2tzIi..."
}
```

* `reward_cents`: what one approved submission on this task pays, in integer US cents.
* `is_gold` / `gold_label`: gold tasks have a known correct label (`gold_label`, otherwise `null`).
* `status` is one of `pending`, `in_progress`, `completed`, `rejected`.

## Submissions

```
GET /v1/submissions?limit=100&cursor=<opaque>
GET /v1/tasks/{task_id}/submissions          (same envelope, one task's submissions)
```

Filters: `task_id`, `annotator_id`.

```json
{
  "data": [
    {
      "id": "sub_00001",
      "task_id": "tsk_0002",
      "annotator_id": "ann_023",
      "submitted_at": "2024-04-09T10:35:50Z",
      "duration_s": 311.3,
      "answer": {"label": "cyclist", "confidence": 0.77,
                 "boxes": [{"x": 485, "y": 391, "w": 121, "h": 113, "label": "car"}]},
      "updated_at": "2024-04-09T10:35:50Z"
    }
  ],
  "next_cursor": null
}
```

## Reviews

```
GET /v1/reviews?page=1&per_page=50
GET /v1/submissions/{submission_id}/reviews  (same envelope, one submission's reviews)
```

Filters: `reviewer_id`, `verdict`, `submission_id`.

```json
{
  "results": [
    {
      "id": "rev_00001",
      "submission_id": "sub_00001",
      "reviewer_id": "ann_017",
      "verdict": "approved",
      "score": 4,
      "comment": null,
      "created_at": "2024-04-09T22:10:50Z",
      "updated_at": "2024-04-09T22:10:50Z"
    }
  ],
  "page": 1, "per_page": 50, "total": 261, "total_pages": 6
}
```

* `verdict` is `approved` or `rejected`.
* A submission can be reviewed more than once (appeals and QA re-reviews), and
  many submissions have not been reviewed yet.

## Results (writable)

The finance system reads payouts from this sink.

```
POST /v1/results
Idempotency-Key: <your key>          (optional, strongly recommended)
{"annotator_id": "ann_001", "period": "...", "amount_cents": 1234}
```

| status | meaning | body |
|---|---|---|
| 201 | stored | the stored record: your fields + `id`, `received_at` |
| 200 | **replay**: a result with this `Idempotency-Key` already exists; nothing new is stored | the originally stored record (even if your body differs) |
| 422 | invalid body (`annotator_id`/`period` must be non-empty strings, `amount_cents` a positive integer) | `{"error": "..."}` |

`GET /v1/results` lists what has been stored (page-numbered, as above).

## Errors

| status | meaning | body |
|---|---|---|
| 400 | bad parameter (page, per_page, offset, limit, cursor, updated_since) | `{"error": "..."}` |
| 401 | see Authentication | `{"error": "..."}` |
| 404 | unknown collection or id | `{"error": "not_found"}` |
| 422 | invalid body (results) | `{"error": "..."}` |
| 429 | rate limited | `{"error": "rate_limited"}` + `Retry-After: <seconds>` |
| 500, 502, 503 | transient upstream failure; safe to retry | `{"error": "upstream_error"}` |

Rate-limited responses also carry `X-RateLimit-Limit`, `X-RateLimit-Remaining`
and `X-RateLimit-Reset`. Under load the API occasionally answers slowly or
returns a `200` whose body is cut off (invalid JSON); both are transient.

## Data quality

The schema above is the *canonical* form. Records are written by several
generations of producers, and the wire format is not always canonical. Look at
`data/recorded/` for real responses. Expect, in any field:

* `null` where a value is expected, or the key missing altogether;
* numbers and booleans sent as strings (`"12"`, `"true"`), and booleans sent as `1`/`0`;
* timestamps in more than one format: ISO-8601 with `Z`, with an offset, without
  any offset (these are UTC), or Unix epoch numbers;
* enumerations and labels with unexpected casing or surrounding whitespace;
* lists sent as comma-separated strings.

A given record always looks the same on every request; the mess is in the data,
not in the transport. Field-specific rules for this integration are in your task description.
