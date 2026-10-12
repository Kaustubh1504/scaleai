"""Mock Labels API for problem 42. Use make_api() in your tests."""

from __future__ import annotations

from kit import MockAPI, error_response


def make_labels(n: int) -> list[dict]:
    return [{"id": f"lbl_{i:03d}", "task_id": f"task_{(i + 1) // 2:03d}", "label": ("cat", "dog", "bird")[i % 3]}
            for i in range(1, n + 1)]


def make_api(n_labels: int = 25, per_page: int = 10, clock=None) -> MockAPI:
    """
    GET /v1/labels?page=N  ->  {"data": [...], "page": N, "total_pages": T, "next_page": N+1 or null}

    api.labels holds every label, in order. Use api.script("GET /v1/labels", [...]) to inject
    faults (503, "429:7", 404, ...) and api.log / api.calls(...) to inspect requests.
    """
    api = MockAPI(clock=clock)
    labels = make_labels(n_labels)
    api.labels = labels
    total_pages = max(1, -(-n_labels // per_page))

    @api.route("GET", "/v1/labels")
    def list_labels(req):
        try:
            page = int(req.params.get("page", "1"))
        except ValueError:
            return error_response(400, "page must be an integer")
        if not 1 <= page <= total_pages:
            return error_response(404, f"no page {page}")
        start = (page - 1) * per_page
        return {"data": labels[start:start + per_page], "page": page, "total_pages": total_pages,
                "next_page": page + 1 if page < total_pages else None}

    return api
