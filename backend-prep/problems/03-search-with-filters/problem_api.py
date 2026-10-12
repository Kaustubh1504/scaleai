"""Mock Orders API for problem 03. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from datetime import datetime, timezone

from kit import MockAPI, error_response

STATUSES = ("pending", "paid", "shipped", "refunded")
SORTS = ("created_at", "-created_at", "total_cents", "-total_cents")
ALLOWED_PARAMS = {"status", "since", "until", "min_total_cents", "include_archived", "sort"}


ORDERS = [
    {"id": "ord_001", "customer": "acme-labs", "status": "paid", "total_cents": 12000, "created_at": "2024-03-01T09:00:00Z", "archived": False},
    {"id": "ord_002", "customer": "zeta-ai", "status": "pending", "total_cents": 0, "created_at": "2024-03-01T18:30:00Z", "archived": False},
    {"id": "ord_003", "customer": "acme-labs", "status": "shipped", "total_cents": 45000, "created_at": "2024-03-02T07:15:00Z", "archived": False},
    {"id": "ord_004", "customer": "northwind", "status": "refunded", "total_cents": 9900, "created_at": "2024-03-02T23:59:59Z", "archived": True},
    {"id": "ord_005", "customer": "zeta-ai", "status": "paid", "total_cents": 2500, "created_at": "2024-03-03T04:00:00Z", "archived": False},
    {"id": "ord_006", "customer": "globex", "status": "shipped", "total_cents": 78000, "created_at": "2024-03-03T12:00:00Z", "archived": True},
    {"id": "ord_007", "customer": "globex", "status": "pending", "total_cents": 1500, "created_at": "2024-03-04T08:45:00Z", "archived": False},
    {"id": "ord_008", "customer": "northwind", "status": "paid", "total_cents": 31000, "created_at": "2024-03-04T16:20:00Z", "archived": False},
    {"id": "ord_009", "customer": "acme-labs", "status": "shipped", "total_cents": 5000, "created_at": "2024-03-05T10:10:00Z", "archived": False},
    {"id": "ord_010", "customer": "initech", "status": "paid", "total_cents": 64000, "created_at": "2024-03-05T21:00:00Z", "archived": True},
    {"id": "ord_011", "customer": "initech", "status": "refunded", "total_cents": 18000, "created_at": "2024-03-06T02:30:00Z", "archived": False},
    {"id": "ord_012", "customer": "zeta-ai", "status": "shipped", "total_cents": 22000, "created_at": "2024-03-06T13:00:00Z", "archived": False},
]


def _parse_utc(value: str) -> datetime | None:
    if not value.endswith("Z"):
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


def search(orders: list[dict], *, statuses=None, since=None, until=None, min_total=None,
           include_archived=False, sort="created_at") -> list[dict]:
    """The server's filtering, also used by the tests to compute expected answers."""
    out = []
    for o in orders:
        created = _parse_utc(o["created_at"])
        if statuses and o["status"] not in statuses:
            continue
        if since is not None and created < since:
            continue
        if until is not None and created >= until:
            continue
        if min_total is not None and o["total_cents"] < min_total:
            continue
        if o["archived"] and not include_archived:
            continue
        out.append(o)
    key = sort.lstrip("-")
    return sorted(out, key=lambda o: (o[key], o["id"]), reverse=sort.startswith("-"))


def make_api(clock=None) -> MockAPI:
    api = MockAPI(clock=clock)
    api.orders = ORDERS

    @api.route("GET", "/v1/orders")
    def list_orders(req):
        multi = req.multi_params
        unknown = sorted({k for k, _ in multi} - ALLOWED_PARAMS)
        if unknown:
            return error_response(400, f"unknown query parameter(s): {unknown}; allowed: {sorted(ALLOWED_PARAMS)}")
        for k in ALLOWED_PARAMS - {"status"}:
            if sum(1 for key, _ in multi if key == k) > 1:
                return error_response(400, f"{k} may only be given once")

        statuses = [v for k, v in multi if k == "status"]
        bad = [s for s in statuses if s not in STATUSES]
        if bad:
            hint = " (send one status= per value, not a comma-separated list)" if any("," in s for s in bad) else ""
            return error_response(400, f"invalid status {bad}; allowed: {list(STATUSES)}{hint}")

        bounds = {}
        for name in ("since", "until"):
            if name in req.params:
                dt = _parse_utc(req.params[name])
                if dt is None:
                    return error_response(400, f"{name} must look like 2024-03-01T09:00:00Z (UTC, 'Z' suffix), got {req.params[name]!r}")
                bounds[name] = dt

        min_total = None
        if "min_total_cents" in req.params:
            raw = req.params["min_total_cents"]
            if not raw.isdigit():
                return error_response(400, f"min_total_cents must be a non-negative integer, got {raw!r}")
            min_total = int(raw)

        include_archived = False
        if "include_archived" in req.params:
            raw = req.params["include_archived"]
            if raw not in ("true", "false"):
                return error_response(400, f"include_archived must be 'true' or 'false', got {raw!r}")
            include_archived = raw == "true"

        sort = req.params.get("sort", "created_at")
        if sort not in SORTS:
            return error_response(400, f"sort must be one of {list(SORTS)}")

        data = search(ORDERS, statuses=statuses, since=bounds.get("since"), until=bounds.get("until"),
                      min_total=min_total, include_archived=include_archived, sort=sort)
        return {"data": data, "count": len(data)}

    return api
