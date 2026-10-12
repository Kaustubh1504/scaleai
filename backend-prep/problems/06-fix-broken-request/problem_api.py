"""Mock Workforce API for problem 06. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

import json

from kit import MockAPI, json_response, paginate_pages

TOKEN = "tok_ops_7c1e"
STATUSES = ("active", "onboarding", "suspended")
LIST_PARAMS = ("page", "per_page", "status")


def make_annotators(n: int) -> list[dict]:
    langs = ["en", "es", "de", "ja", "hi", "fr", "pt"]
    return [{"id": f"ann_{i:03d}", "name": f"Annotator {i}",
             "status": "active" if i % 4 else ("suspended" if i % 8 == 0 else "onboarding"),
             "languages": [langs[i % len(langs)], "en"] if i % len(langs) else ["en"]}
            for i in range(1, n + 1)]


def _problem(status: int, error: str, message: str, headers: dict | None = None, **extra):
    return json_response({"error": error, "message": message, **extra}, status, headers)


def make_api(n_annotators: int = 23, n_tasks: int = 8, clock=None) -> MockAPI:
    api = MockAPI(clock=clock)
    annotators = make_annotators(n_annotators)
    tasks = {f"task_{i:03d}": {"id": f"task_{i:03d}", "kind": "bbox"} for i in range(1, n_tasks + 1)}
    assignments: list[dict] = []
    api.annotators, api.tasks, api.assignments = annotators, tasks, assignments

    def check_auth(req):
        value = req.header("authorization")
        if value is None:
            return _problem(401, "missing_authorization", "send an Authorization header",
                            {"WWW-Authenticate": 'Bearer realm="workforce"'})
        if value != f"Bearer {TOKEN}":
            scheme_ok = value.startswith("Bearer ")
            return _problem(401, "invalid_token",
                            "token not recognised" if scheme_ok else
                            "Authorization header must use the Bearer scheme",
                            {"WWW-Authenticate": 'Bearer realm="workforce", error="invalid_token"'})
        return None

    @api.route("GET", "/v1/annotators")
    def list_annotators(req):
        if (denied := check_auth(req)) is not None:
            return denied
        unknown = [k for k, _ in req.multi_params if k not in LIST_PARAMS]
        if unknown:
            return _problem(400, "unknown_parameter", f"unknown query parameter {unknown[0]!r}",
                            allowed=list(LIST_PARAMS))
        try:
            page = int(req.params.get("page", "1"))
            per_page = int(req.params.get("per_page", "10"))
        except ValueError:
            return _problem(400, "invalid_parameter", "page and per_page must be integers")
        if page < 1 or not 1 <= per_page <= 100:
            return _problem(400, "invalid_parameter", "page must be >= 1 and per_page between 1 and 100")
        rows = annotators
        status = req.params.get("status")
        if status is not None:
            if status not in STATUSES:
                return _problem(400, "invalid_parameter", f"status must be one of {list(STATUSES)}")
            rows = [a for a in rows if a["status"] == status]
        return paginate_pages(rows, page, per_page)

    @api.route("POST", "/v1/tasks/{task_id}/assignments")
    def assign(req, task_id):
        if (denied := check_auth(req)) is not None:
            return denied
        ctype = (req.header("content-type") or "").split(";")[0].strip()
        if ctype != "application/json":
            return _problem(415, "unsupported_media_type",
                            f"expected a JSON body (Content-Type: application/json), got {ctype or 'no content-type'}")
        try:
            body = json.loads(req.body)
        except ValueError:
            return _problem(400, "invalid_json", "request body is not valid JSON")
        if task_id not in tasks:
            return _problem(404, "not_found", f"task {task_id!r} not found")
        annotator = next((a for a in annotators if a["id"] == body.get("annotator_id")), None)
        if annotator is None:
            return _problem(422, "invalid_annotator", f"unknown annotator_id {body.get('annotator_id')!r}")
        record = {"id": f"asg_{len(assignments) + 1:04d}", "task_id": task_id,
                  "annotator_id": annotator["id"], "status": "assigned"}
        assignments.append(record)
        return 201, record

    return api
