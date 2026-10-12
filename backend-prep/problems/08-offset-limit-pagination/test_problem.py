import pytest

from problem_api import API_KEY, make_api


def ids(items):
    return [a["id"] for a in items]


def offsets(api):
    return [c.params.get("offset") for c in api.calls("GET", "/v1/annotations")]


def test_fetches_everything_in_order(sol):
    """Returns all 130 annotations, in API order"""
    api = make_api(n_annotations=130)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=50)
    assert ids(out) == ids(api.annotations), "annotations missing, duplicated or out of order"


def test_sends_offset_limit_and_key(sol):
    """Sends offset 0, 50, 100 with limit=50 and the API key, and stops after the short page"""
    api = make_api(n_annotations=130)
    sol.fetch_all_annotations(api.client(), API_KEY, limit=50)
    assert offsets(api) == ["0", "50", "100"], f"got offsets {offsets(api)}"
    assert all(c.params.get("limit") == "50" for c in api.log), "pass limit on every request"
    assert all(c.header("x-api-key") == API_KEY for c in api.log), "send X-API-Key on every request"


def test_limit_capped_by_server(sol):
    """Asking for limit=100 gets 50 per page: advances by 50 and misses nothing"""
    api = make_api(n_annotations=130)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=100)
    assert ids(out) == ids(api.annotations), (
        f"got {len(out)} of 130: advancing offset by the requested limit skips the items the server capped away")
    assert offsets(api) == ["0", "50", "100"], f"advance by len(items); got offsets {offsets(api)}"


def test_small_limit(sol):
    """Works with a small page size (limit=7 over 30 annotations)"""
    api = make_api(n_annotations=30)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=7)
    assert ids(out) == ids(api.annotations)
    assert offsets(api) == ["0", "7", "14", "21", "28"], f"got offsets {offsets(api)}"


def test_total_too_low(sol):
    """total says 60 but 130 exist: keeps going and returns all 130"""
    api = make_api(n_annotations=130, reported_total=60)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=50)
    assert len(out) == 130, f"got {len(out)}: don't stop because of `total`, it is stale"


def test_total_too_high(sol):
    """total says 500 but 130 exist: stops on the short page after 3 requests"""
    api = make_api(n_annotations=130, reported_total=500)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=50)
    assert len(out) == 130
    assert len(api.log) == 3, f"made {len(api.log)} requests: the short third page is the end, whatever total says"


def test_exact_multiple(sol):
    """100 annotations at 50 per page: the third request comes back empty and ends the crawl"""
    api = make_api(n_annotations=100)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=50)
    assert ids(out) == ids(api.annotations)
    assert offsets(api) == ["0", "50", "100"], f"got offsets {offsets(api)}"


def test_exact_multiple_with_capped_limit(sol):
    """100 annotations, asking limit=100: full capped pages are not mistaken for the end"""
    api = make_api(n_annotations=100, reported_total=40)
    out = sol.fetch_all_annotations(api.client(), API_KEY, limit=100)
    assert len(out) == 100, f"got {len(out)}: 50 < 100 is not a short page, the server's limit is 50"
    assert offsets(api) == ["0", "50", "100"], f"got offsets {offsets(api)}"


def test_empty_collection(sol):
    """No annotations: returns [] after one request"""
    api = make_api(n_annotations=0)
    assert sol.fetch_all_annotations(api.client(), API_KEY) == []
    assert len(api.log) == 1


def test_error_raises_api_error(sol):
    """A 500 on page 2 raises ApiError(500) with path /v1/annotations"""
    api = make_api(n_annotations=130)
    api.script("GET /v1/annotations", ["pass", 500])
    with pytest.raises(sol.ApiError) as exc:
        sol.fetch_all_annotations(api.client(), API_KEY, limit=50)
    assert exc.value.status == 500
    assert exc.value.path == "/v1/annotations"
