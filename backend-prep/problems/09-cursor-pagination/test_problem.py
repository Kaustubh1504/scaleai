import inspect

import pytest

from problem_api import API_KEY, make_api


def ids(events):
    return [e["id"] for e in events]


def test_fetches_every_event_in_order(sol):
    """Returns all 123 events, in API order"""
    api = make_api(n_events=123)
    events = sol.fetch_all_events(api.client(), API_KEY, limit=50)
    assert ids(events) == ids(api.events), "events missing, duplicated or out of order"


def test_request_count_and_limit(sol):
    """Makes exactly ceil(n / limit) requests and sends `limit` every time"""
    api = make_api(n_events=123)
    sol.fetch_all_events(api.client(), API_KEY, limit=50)
    calls = api.calls("GET", "/v1/events")
    assert len(calls) == 3, f"expected 3 requests for 123 events at limit=50, made {len(calls)}"
    assert all(c.params.get("limit") == "50" for c in calls), "every request must pass limit=50"
    assert "cursor" not in calls[0].params, "the first request must not send a cursor"


def test_sends_api_key(sol):
    """Sends the X-API-Key header on every request"""
    api = make_api(n_events=10)
    sol.fetch_all_events(api.client(), API_KEY, limit=4)
    assert all(c.header("x-api-key") == API_KEY for c in api.log)


def test_exact_multiple_of_limit(sol):
    """Handles a total that divides evenly by the page size (no extra or missing page)"""
    api = make_api(n_events=100)
    events = sol.fetch_all_events(api.client(), API_KEY, limit=25)
    assert len(events) == 100
    assert len(api.log) == 4


def test_empty_collection(sol):
    """An API with zero events returns [] after one request"""
    api = make_api(n_events=0)
    assert sol.fetch_all_events(api.client(), API_KEY) == []
    assert len(api.log) == 1


def test_is_lazy_generator(sol):
    """iter_events is a generator and fetches page 2 only when page 1 is used up"""
    api = make_api(n_events=30)
    gen = sol.iter_events(api.client(), API_KEY, limit=10)
    assert inspect.isgenerator(gen), "iter_events must be a generator (use yield)"
    assert len(api.log) == 0, "no request should be made before the first next()"
    first = next(gen)
    assert first["id"] == "evt_0001"
    assert len(api.log) == 1, "only one page should be fetched to produce the first event"


def test_bad_key_raises_api_error(sol):
    """A 401 raises ApiError with status 401 and path /v1/events"""
    api = make_api(n_events=5)
    with pytest.raises(sol.ApiError) as exc:
        sol.fetch_all_events(api.client(), "wrong-key")
    assert exc.value.status == 401
    assert exc.value.path == "/v1/events"


def test_server_error_mid_crawl(sol):
    """A 503 on page 2 raises ApiError(503) (no retries in this problem)"""
    api = make_api(n_events=30)
    api.script("GET /v1/events", ["pass", 503])
    with pytest.raises(sol.ApiError) as exc:
        sol.fetch_all_events(api.client(), API_KEY, limit=10)
    assert exc.value.status == 503


def test_detects_cursor_loop(sol):
    """A server that repeats a cursor raises PaginationLoopError instead of looping forever"""
    api = make_api(n_events=100, loop_at_page=3)
    with pytest.raises(sol.PaginationLoopError):
        sol.fetch_all_events(api.client(), API_KEY, limit=10)
    assert len(api.log) <= 4, f"loop detected too late: made {len(api.log)} requests"
