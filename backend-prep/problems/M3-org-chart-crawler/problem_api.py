"""Mock org-directory API for M3. Tests and your __main__ block both use make_api().

    api = make_api()                                  # the sample org chart, no auth (Part 1)
    api = make_api(auth=True, token_ttl_s=20, latency_s=1.0, clock=clock)   # Part 2
    api = make_api(rate_limit=3, clock=clock)         # Part 3: 3 /v1 requests per second
    api = make_api(orgs, members, forbidden={"org_x"})

``api.tokens`` is the TokenIssuer, ``api.limiter`` the FixedWindowLimiter (or None).
"""

from __future__ import annotations

from typing import Any

from kit import FakeClock, FixedWindowLimiter, MockAPI, TokenIssuer, error_response, json_response, paginate_cursor

CLIENT_ID = "org-crawler"
CLIENT_SECRET = "hunter2"
LIMIT_MAX = 50


def person(n: int) -> dict:
    return {"person_id": f"p{n:03d}", "name": f"Person {n}", "role": ("ic", "manager")[n % 5 == 0]}


def sample_orgs() -> dict[str, dict]:
    return {
        "org_root": {"name": "Acme", "children": ["org_eng", "org_ops", "org_legacy"]},
        "org_eng": {"name": "Engineering", "children": ["org_platform", "org_ml"]},
        "org_ops": {"name": "Operations", "children": ["org_support", "org_legal"]},
        "org_platform": {"name": "Platform", "children": []},
        "org_ml": {"name": "Machine Learning", "children": ["org_research"]},
        "org_research": {"name": "Research", "children": ["org_ml", "org_platform"]},   # cycle + shared child
        "org_support": {"name": "Support", "children": []},
        "org_legal": {"name": "Legal", "children": []},
        # "org_legacy" is referenced but no longer exists (404)
    }


def sample_members() -> dict[str, list[dict]]:
    ranges = {"org_root": [1, 2], "org_eng": [3, 4, 5], "org_ops": [6],
              "org_platform": list(range(7, 15)) + [5], "org_ml": [15, 16, 17],
              "org_research": [18, 19, 15], "org_support": list(range(20, 45)), "org_legal": [45, 46]}
    return {org: [person(n) for n in ns] for org, ns in ranges.items()}


def make_api(orgs: dict[str, dict] | None = None, members: dict[str, list[dict]] | None = None, *,
             clock: Any = None, latency_s: float = 0.0, auth: bool = False, token_ttl_s: float = 3600.0,
             rate_limit: int | None = None, forbidden: set[str] | frozenset[str] = frozenset()) -> MockAPI:
    clock = clock if clock is not None else FakeClock()
    orgs = sample_orgs() if orgs is None else orgs
    members = sample_members() if members is None else members
    api = MockAPI(clock=clock, latency_s=latency_s)
    api.tokens = TokenIssuer(clock, token_ttl_s)
    api.limiter = FixedWindowLimiter(clock, rate_limit, 1.0) if rate_limit else None

    def guarded(req, org_id: str, body_fn):
        headers: dict[str, str] = {}
        if api.limiter is not None:
            allowed, headers = api.limiter.check()
            if not allowed:
                return error_response(429, headers=headers)
        if auth and not api.tokens.valid(req.header("authorization")):
            return error_response(401, "missing or expired bearer token", headers)
        if org_id not in orgs:
            return error_response(404, f"no org {org_id}", headers)
        if org_id in forbidden:
            return error_response(403, f"no access to {org_id}", headers)
        status, body = body_fn()
        return json_response(body, status, headers)

    @api.route("POST", "/oauth/token")
    def token(req):
        try:
            body = req.json() or {}
        except ValueError:
            return error_response(400, "body must be JSON")
        if body.get("client_id") != CLIENT_ID or body.get("client_secret") != CLIENT_SECRET:
            return error_response(401, "invalid client credentials")
        return api.tokens.issue()

    @api.route("GET", "/v1/orgs/{org_id}")
    def get_org(req, org_id):
        return guarded(req, org_id, lambda: (200, {"id": org_id, **orgs[org_id]}))

    @api.route("GET", "/v1/orgs/{org_id}/members")
    def get_members(req, org_id):
        def page():
            try:
                limit = int(req.params.get("limit", "20"))
            except ValueError:
                return 400, {"error": "limit must be an integer"}
            if not 1 <= limit <= LIMIT_MAX:
                return 400, {"error": f"1 <= limit <= {LIMIT_MAX}"}
            try:
                return 200, paginate_cursor(members.get(org_id, []), req.params.get("cursor") or None, limit)
            except ValueError:
                return 400, {"error": "invalid cursor"}
        return guarded(req, org_id, page)

    return api
