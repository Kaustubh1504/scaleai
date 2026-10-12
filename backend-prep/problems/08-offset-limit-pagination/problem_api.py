"""Mock Annotations API for problem 08. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from kit import MockAPI, error_response

API_KEY = "key_live_123"
SERVER_MAX_LIMIT = 50


def make_annotations(n: int) -> list[dict]:
    labels = ("cat", "dog", "car", "person", "tree")
    return [{"id": f"ann_{i:05d}", "task_id": f"task_{(i - 1) // 4 + 1:04d}", "label": labels[i % 5],
             "annotator": f"user_{i % 7 + 1}"} for i in range(1, n + 1)]


def make_api(n_annotations: int = 130, *, reported_total: int | None = None, clock=None) -> MockAPI:
    """
    n_annotations  : how many annotations really exist.
    reported_total : what the server claims in "total" (stale count); defaults to the truth.

    The server silently caps ``limit`` at SERVER_MAX_LIMIT and echoes the limit it applied.
    """
    api = MockAPI(clock=clock)
    annotations = make_annotations(n_annotations)
    api.annotations = annotations

    @api.route("GET", "/v1/annotations")
    def list_annotations(req):
        if req.header("x-api-key") != API_KEY:
            return error_response(401, "missing or invalid X-API-Key")
        try:
            offset = int(req.params.get("offset", "0"))
            limit = int(req.params.get("limit", "20"))
        except ValueError:
            return error_response(400, "offset and limit must be integers")
        if offset < 0 or limit < 1:
            return error_response(400, "offset must be >= 0 and limit >= 1")
        limit = min(limit, SERVER_MAX_LIMIT)
        total = len(annotations) if reported_total is None else reported_total
        return {"items": annotations[offset:offset + limit], "offset": offset, "limit": limit, "total": total}

    return api
