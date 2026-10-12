"""Mock annotation-platform API for M1. Tests and your __main__ block both use make_api().

    api = make_api()                       # small sample dataset (clean)
    api = make_api(messy_sample_data())    # the same kind of data, with messy wire values
    api = make_api({"annotators": [...], "tasks": [...], "submissions": [...]})

The mock serves the records exactly as given (no cleaning). ``api.payouts`` maps
Idempotency-Key -> stored payout; ``api.tokens.issued`` counts issued tokens.
"""

from __future__ import annotations

from typing import Any

from kit import FakeClock, MockAPI, TokenIssuer, error_response, paginate_cursor, paginate_offset, paginate_pages

CLIENT_ID = "payouts-job"
CLIENT_SECRET = "s3cr3t"
PER_PAGE_MAX = 25   # /v1/annotators
LIMIT_MAX = 50      # /v1/tasks and /v1/submissions


def make_api(data: dict[str, list[dict]] | None = None, *, clock: Any = None, latency_s: float = 0.0,
             token_ttl_s: float = 3600.0) -> MockAPI:
    clock = clock if clock is not None else FakeClock()
    data = data if data is not None else sample_data()
    api = MockAPI(clock=clock, latency_s=latency_s)
    tokens = TokenIssuer(clock, token_ttl_s)
    api.tokens = tokens
    api.data = data
    api.payouts: dict[str, dict] = {}

    def int_param(req, name: str, default: int, lo: int, hi: int | None) -> int | None:
        raw = req.params.get(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            return None
        if value < lo or (hi is not None and value > hi):
            return None
        return value

    def unauthorized(req) -> bool:
        return not tokens.valid(req.header("authorization"))

    @api.route("POST", "/oauth/token")
    def token(req):
        try:
            body = req.json() or {}
        except ValueError:
            return error_response(400, "body must be JSON")
        if body.get("client_id") != CLIENT_ID or body.get("client_secret") != CLIENT_SECRET:
            return error_response(401, "invalid client credentials")
        return tokens.issue()

    @api.route("GET", "/v1/annotators")
    def annotators(req):
        if unauthorized(req):
            return error_response(401, "missing or expired bearer token")
        page = int_param(req, "page", 1, 1, None)
        per_page = int_param(req, "per_page", 10, 1, PER_PAGE_MAX)
        if page is None or per_page is None:
            return error_response(400, f"page >= 1 and 1 <= per_page <= {PER_PAGE_MAX}")
        return paginate_pages(data["annotators"], page, per_page)

    @api.route("GET", "/v1/tasks")
    def tasks(req):
        if unauthorized(req):
            return error_response(401, "missing or expired bearer token")
        offset = int_param(req, "offset", 0, 0, None)
        limit = int_param(req, "limit", 20, 1, LIMIT_MAX)
        if offset is None or limit is None:
            return error_response(400, f"offset >= 0 and 1 <= limit <= {LIMIT_MAX}")
        return paginate_offset(data["tasks"], offset, limit)

    @api.route("GET", "/v1/submissions")
    def submissions(req):
        if unauthorized(req):
            return error_response(401, "missing or expired bearer token")
        limit = int_param(req, "limit", 20, 1, LIMIT_MAX)
        if limit is None:
            return error_response(400, f"1 <= limit <= {LIMIT_MAX}")
        try:
            return paginate_cursor(data["submissions"], req.params.get("cursor") or None, limit)
        except ValueError:
            return error_response(400, "invalid cursor")

    @api.route("POST", "/v1/payouts")
    def create_payout(req):
        if unauthorized(req):
            return error_response(401, "missing or expired bearer token")
        key = req.header("idempotency-key")
        if not key:
            return error_response(400, "Idempotency-Key header is required")
        try:
            body = req.json() or {}
        except ValueError:
            return error_response(400, "body must be JSON")
        amount = body.get("amount_cents")
        if (not isinstance(body.get("annotator_id"), str) or not isinstance(body.get("period"), str)
                or not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0):
            return error_response(422, "annotator_id (str), period (str), amount_cents (int > 0) are required")
        fields = {k: body[k] for k in ("annotator_id", "period", "amount_cents")}
        if key in api.payouts:
            stored = api.payouts[key]
            if {k: stored[k] for k in fields} != fields:
                return error_response(409, "Idempotency-Key reused with a different body")
            return 200, stored
        record = {"id": f"pay_{len(api.payouts) + 1:04d}", **fields}
        api.payouts[key] = record
        return 201, record

    return api


# ------------------------------------------------------------------ sample data


def _sub(sid, ann, task, at, *reviews):
    return {"id": sid, "annotator_id": ann, "task_id": task, "submitted_at": at,
            "reviews": [{"id": r, "verdict": v, "reviewed_at": t} for r, v, t in reviews]}


def sample_data() -> dict[str, list[dict]]:
    """Clean data. Period of interest: 2024-05-01 .. 2024-05-15 (UTC)."""
    annotators = [{"id": f"ann_{i:03d}", "name": n, "on_hold": False}
                  for i, n in enumerate(["Ana", "Bo", "Chen", "Dee", "Eli", "Fay"], start=1)]
    tasks = [{"id": f"task_{i:03d}", "project": "chat-ranking", "reward_cents": r}
             for i, r in enumerate([25, 40, 15, 60, 30, 25, 50, 10], start=1)]
    submissions = [
        _sub("sub_0001", "ann_001", "task_001", "2024-05-01T00:00:00Z", ("rev_0001", "approved", "2024-05-02T09:00:00Z")),
        _sub("sub_0002", "ann_001", "task_002", "2024-05-03T10:15:00Z", ("rev_0002", "rejected", "2024-05-04T09:00:00Z"),
             ("rev_0003", "approved", "2024-05-05T09:00:00Z")),
        _sub("sub_0003", "ann_002", "task_003", "2024-05-06T08:00:00Z"),
        _sub("sub_0004", "ann_002", "task_004", "2024-05-07T08:00:00Z", ("rev_0004", "approved", "2024-05-08T12:00:00Z"),
             ("rev_0005", "rejected", "2024-05-08T12:00:00Z")),
        _sub("sub_0005", "ann_003", "task_005", "2024-05-14T23:59:59Z", ("rev_0006", "approved", "2024-05-20T10:00:00Z")),
        _sub("sub_0006", "ann_003", "task_006", "2024-05-15T00:00:00Z", ("rev_0007", "approved", "2024-05-16T10:00:00Z")),
        _sub("sub_0007", "ann_004", "task_007", "2024-04-30T23:59:59Z", ("rev_0008", "approved", "2024-05-01T10:00:00Z")),
        _sub("sub_0008", "ann_005", "task_008", "2024-05-09T16:45:00Z", ("rev_0009", "approved", "2024-05-10T10:00:00Z")),
        _sub("sub_0009", "ann_005", "task_001", "2024-05-10T16:45:00Z", ("rev_0010", "approved", "2024-05-11T10:00:00Z")),
        _sub("sub_0010", "ann_006", "task_002", "2024-05-11T07:30:00Z", ("rev_0011", "rejected", "2024-05-12T10:00:00Z")),
    ]
    return {"annotators": annotators, "tasks": tasks, "submissions": submissions}


def messy_sample_data() -> dict[str, list[dict]]:
    """The same platform on a bad day: the wire values Part 2 is about."""
    data = sample_data()
    data["annotators"][1]["on_hold"] = "TRUE"
    data["annotators"][4]["on_hold"] = "no"
    data["tasks"][0]["reward_cents"] = " 25 "
    data["tasks"][4]["reward_cents"] = "N/A"
    subs = data["submissions"]
    subs[0]["submitted_at"] = 1714521600            # epoch seconds
    subs[1]["submitted_at"] = 1714731300000         # epoch milliseconds
    subs[2]["submitted_at"] = "2024-05-06 10:00:00+02:00"
    subs[3]["reviews"][0]["verdict"] = " Approved "
    subs[7]["submitted_at"] = "yesterday"
    subs.append(dict(subs[8]))                      # the same submission served twice
    return data
