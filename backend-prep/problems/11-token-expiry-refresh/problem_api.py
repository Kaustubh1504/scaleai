"""Mock Tasks API with short-lived OAuth tokens for problem 11. Tests and your __main__ use make_api()."""

from __future__ import annotations

from urllib.parse import parse_qsl

from kit import MockAPI, TokenIssuer, error_response, paginate_pages

CLIENT_ID = "crawler"
CLIENT_SECRET = "s3cr3t_Kp9wQ2"
TOKEN_TTL_S = 10.0
LATENCY_S = 1.0


def make_tasks(n: int) -> list[dict]:
    statuses = ("pending", "in_review", "done")
    return [{"id": f"task_{i:04d}", "status": statuses[i % 3], "priority": i % 5} for i in range(1, n + 1)]


def make_api(clock, *, n_tasks: int = 60, refresh_broken: bool = False) -> MockAPI:
    """
    Every request (token requests included) takes LATENCY_S of fake time; the
    clock moves forward *before* the server handles it.

    refresh_broken : every refresh_token grant fails with 400 invalid_grant.

    Test helpers:
      api.issuer             the kit.TokenIssuer (api.issuer.revoke_all() kills access tokens)
      api.issued             {access_token: (issued_at, expires_at)} in server time
      api.revoke_refresh_tokens()
    """
    api = MockAPI(clock=clock, latency_s=LATENCY_S)
    issuer = TokenIssuer(clock, ttl_s=TOKEN_TTL_S)
    tasks = make_tasks(n_tasks)
    by_id = {t["id"]: t for t in tasks}
    refresh_tokens: set[str] = set()
    counter = {"rt": 0}
    api.issuer = issuer
    api.tasks = tasks
    api.issued: dict[str, tuple[float, float]] = {}
    api.revoke_refresh_tokens = refresh_tokens.clear

    def issue() -> dict:
        tok = issuer.issue()
        now = clock.time()
        api.issued[tok["access_token"]] = (now, now + TOKEN_TTL_S)
        counter["rt"] += 1
        rt = f"rt_{counter['rt']:05d}"
        refresh_tokens.add(rt)
        return {**tok, "expires_in": int(tok["expires_in"]), "refresh_token": rt}

    @api.route("POST", "/oauth/token")
    def token(req):
        ctype = (req.header("content-type") or "").split(";")[0].strip()
        if ctype != "application/x-www-form-urlencoded":
            return 400, {"error": "invalid_request", "error_description": "body must be form-encoded"}
        form = dict(parse_qsl(req.body.decode()))
        if form.get("client_id") != CLIENT_ID or form.get("client_secret") != CLIENT_SECRET:
            return 401, {"error": "invalid_client"}
        grant = form.get("grant_type")
        if grant == "client_credentials":
            return issue()
        if grant == "refresh_token":
            rt = form.get("refresh_token")
            if refresh_broken or rt not in refresh_tokens:
                return 400, {"error": "invalid_grant"}
            refresh_tokens.discard(rt)  # refresh tokens are single-use (rotated)
            return issue()
        return 400, {"error": "unsupported_grant_type"}

    def authed(req) -> bool:
        return issuer.valid(req.header("authorization"))

    @api.route("GET", "/v1/tasks")
    def list_tasks(req):
        if not authed(req):
            return error_response(401, "missing, invalid or expired bearer token")
        page = int(req.params.get("page", "1"))
        per_page = int(req.params.get("per_page", "10"))
        return paginate_pages(tasks, page, per_page)

    @api.route("GET", "/v1/tasks/{task_id}")
    def get_task(req, task_id):
        if not authed(req):
            return error_response(401, "missing, invalid or expired bearer token")
        if task_id not in by_id:
            return error_response(404, f"no task {task_id}")
        return by_id[task_id]

    return api
