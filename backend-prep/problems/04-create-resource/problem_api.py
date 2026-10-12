"""Mock Projects API for problem 04 (FastAPI-style errors). Tests and your __main__ use make_api()."""

from __future__ import annotations

import json

from kit import MockAPI

TOKEN = "tok_live_9f2c"

EXISTING = [
    {"id": "prj_001", "name": "Driving scenes v3", "description": "Lidar + camera boxes", "tags": ["vision"],
     "status": "active", "created_at": "2024-02-11T10:00:00Z"},
    {"id": "prj_002", "name": "Support chat RLHF", "description": None, "tags": ["llm", "rlhf"],
     "status": "active", "created_at": "2024-03-02T15:30:00Z"},
]


def _err(loc: list, msg: str, typ: str) -> dict:
    return {"loc": loc, "msg": msg, "type": typ}


def _check_str(value, loc: list, max_len: int) -> list[dict]:
    if not isinstance(value, str):
        return [_err(loc, "Input should be a valid string", "string_type")]
    if len(value) < 1:
        return [_err(loc, "String should have at least 1 character", "string_too_short")]
    if len(value) > max_len:
        return [_err(loc, f"String should have at most {max_len} characters", "string_too_long")]
    return []


def validate(body) -> list[dict]:
    """FastAPI/pydantic-style validation errors for a ProjectCreate body."""
    if not isinstance(body, dict):
        return [_err(["body"], "Input should be a valid dictionary or object to extract fields from",
                     "model_attributes_type")]
    errors: list[dict] = []
    if "name" not in body:
        errors.append(_err(["body", "name"], "Field required", "missing"))
    else:
        errors += _check_str(body["name"], ["body", "name"], 80)
    if body.get("description") is not None:
        errors += _check_str(body["description"], ["body", "description"], 500)
    if body.get("tags") is not None:
        tags = body["tags"]
        if not isinstance(tags, list):
            errors.append(_err(["body", "tags"], "Input should be a valid list", "list_type"))
        else:
            if len(tags) > 10:
                errors.append(_err(["body", "tags"], "List should have at most 10 items after validation", "too_long"))
            for i, tag in enumerate(tags):
                errors += _check_str(tag, ["body", "tags", i], 20)
    for key in body:
        if key not in {"name", "description", "tags"}:
            errors.append(_err(["body", key], "Extra inputs are not permitted", "extra_forbidden"))
    return errors


def make_api(clock=None) -> MockAPI:
    api = MockAPI(clock=clock)
    projects = [dict(p) for p in EXISTING]
    api.projects = projects

    @api.route("POST", "/v1/projects")
    def create_project(req):
        if req.header("authorization") != f"Bearer {TOKEN}":
            return 401, {"detail": "Not authenticated"}, {"WWW-Authenticate": "Bearer"}
        ctype = (req.header("content-type") or "").split(";")[0].strip()
        if ctype != "application/json":
            return 415, {"detail": f"Unsupported Media Type: expected application/json, got {ctype or 'nothing'}"}
        try:
            body = json.loads(req.body or b"null")
        except ValueError:
            return 400, {"detail": "There was an error parsing the body"}
        errors = validate(body)
        if errors:
            return 422, {"detail": errors}
        clash = next((p for p in projects if p["name"].casefold() == body["name"].casefold()), None)
        if clash is not None:
            return 409, {"detail": f"a project named {clash['name']!r} already exists", "existing_id": clash["id"]}
        project = {
            "id": f"prj_{len(projects) + 1:03d}",
            "name": body["name"],
            "description": body.get("description"),
            "tags": body.get("tags") or [],
            "status": "active",
            "created_at": "2024-03-10T12:00:00Z",
        }
        projects.append(project)
        return 201, project, {"Location": f"/v1/projects/{project['id']}"}

    return api
