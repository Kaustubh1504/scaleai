"""Mock Events API for problem 09. Tests and your __main__ block both use make_api()."""

from __future__ import annotations

from kit import MockAPI, error_response, paginate_cursor

API_KEY = "key_live_123"


def make_events(n: int) -> list[dict]:
    return [{"id": f"evt_{i:04d}", "type": ("created", "updated", "deleted")[i % 3], "seq": i} for i in range(1, n + 1)]


def make_api(n_events: int = 123, *, loop_at_page: int | None = None, clock=None) -> MockAPI:
    """
    n_events     : how many events the API holds.
    loop_at_page : if set, the server is buggy and that page (1-based) hands back
                   the cursor it was called with, so a naive client loops forever.
    """
    api = MockAPI(clock=clock)
    events = make_events(n_events)
    api.events = events
    pages_served = {"n": 0}

    @api.route("GET", "/v1/events")
    def list_events(req):
        if req.header("x-api-key") != API_KEY:
            return error_response(401, "missing or invalid X-API-Key")
        try:
            limit = int(req.params.get("limit", "20"))
        except ValueError:
            return error_response(400, "limit must be an integer")
        if not 1 <= limit <= 100:
            return error_response(400, "limit must be between 1 and 100")
        cursor = req.params.get("cursor") or None
        try:
            page = paginate_cursor(events, cursor, limit)
        except ValueError:
            return error_response(400, "invalid cursor")
        pages_served["n"] += 1
        if loop_at_page is not None and pages_served["n"] >= loop_at_page and cursor:
            page["next_cursor"] = cursor
        return page

    return api
