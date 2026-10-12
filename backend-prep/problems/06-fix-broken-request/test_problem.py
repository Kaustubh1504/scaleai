import httpx
import pytest

from problem_api import TOKEN, make_api


def attempt(fn, *args, **kwargs):
    """Call fn, ignoring HTTP errors, so a test can inspect what was sent."""
    try:
        return fn(*args, **kwargs)
    except httpx.HTTPStatusError:
        return None


def test_sends_bearer_token(sol):
    """Requests send 'Authorization: Bearer <token>'"""
    api = make_api()
    attempt(sol.list_annotators, api.client(), TOKEN)
    attempt(sol.assign_task, api.client(), TOKEN, "task_001", "ann_001")
    sent = {c.key: c.header("authorization") for c in api.log}
    assert sent and all(v == f"Bearer {TOKEN}" for v in sent.values()), \
        f"Authorization headers sent: {sent} (look at the 401's WWW-Authenticate header and message)"


def test_sends_per_page(sol):
    """list_annotators sends the page size as per_page"""
    api = make_api()
    attempt(sol.list_annotators, api.client(), TOKEN, page_size=10)
    first = api.calls("GET", "/v1/annotators")[0]
    assert first.params.get("per_page") == "10" and "per-page" not in first.params, \
        f"query sent: {first.multi_params} (the 400 body lists the allowed params)"


def test_assign_sends_json(sol):
    """assign_task sends a JSON body {"annotator_id": ...}"""
    api = make_api()
    attempt(sol.assign_task, api.client(), TOKEN, "task_001", "ann_001")
    call = api.calls("POST", "/v1/tasks/task_001/assignments")[0]
    assert (call.header("content-type") or "").startswith("application/json"), \
        f"content-type was {call.header('content-type')!r} (a 415 means the server can't read that body format)"
    assert call.json() == {"annotator_id": "ann_001"}


def test_lists_all_annotators_across_pages(sol):
    """list_annotators returns all 23 annotators in id order using pages 1, 2, 3"""
    api = make_api(n_annotators=23)
    got = sol.list_annotators(api.client(), TOKEN, page_size=10)
    assert [a["id"] for a in got] == [a["id"] for a in api.annotators]
    pages = [c.params.get("page") for c in api.calls("GET", "/v1/annotators")]
    assert pages == ["1", "2", "3"], f"pages requested: {pages}"


def test_single_page(sol):
    """With page_size=100 everything comes back in one request"""
    api = make_api(n_annotators=23)
    got = sol.list_annotators(api.client(), TOKEN, page_size=100)
    assert len(got) == 23 and len(api.log) == 1


def test_status_filter(sol):
    """status="active" returns only active annotators"""
    api = make_api(n_annotators=23)
    got = sol.list_annotators(api.client(), TOKEN, status="active", page_size=5)
    assert [a["id"] for a in got] == [a["id"] for a in api.annotators if a["status"] == "active"]
    assert all(c.params.get("status") == "active" for c in api.log)


def test_assign_task_returns_assignment(sol):
    """assign_task returns the 201 assignment and the server records it"""
    api = make_api()
    got = sol.assign_task(api.client(), TOKEN, "task_002", "ann_003")
    assert got == {"id": "asg_0001", "task_id": "task_002", "annotator_id": "ann_003", "status": "assigned"}
    assert api.assignments == [got]


def test_round_robin_wraps_around(sol):
    """assign_round_robin cycles through active annotators in id order"""
    api = make_api(n_annotators=9, n_tasks=9)
    tasks = [f"task_{i:03d}" for i in range(1, 10)]
    got = sol.assign_round_robin(api.client(), TOKEN, tasks)
    active = [a["id"] for a in api.annotators if a["status"] == "active"]  # 7 of them
    expected = [(t, active[i % len(active)]) for i, t in enumerate(tasks)]
    assert [(a["task_id"], a["annotator_id"]) for a in got] == expected


def test_errors_still_raise(sol):
    """An unknown task still raises httpx.HTTPStatusError (404)"""
    api = make_api()
    with pytest.raises(httpx.HTTPStatusError) as exc:
        sol.assign_task(api.client(), TOKEN, "task_999", "ann_001")
    assert exc.value.response.status_code == 404, \
        f"expected a 404 for an unknown task, got {exc.value.response.status_code}: {exc.value.response.text}"


def test_no_active_annotators(sol):
    """assign_round_robin raises ValueError when nobody is active"""
    api = make_api(n_annotators=0)
    with pytest.raises(ValueError):
        sol.assign_round_robin(api.client(), TOKEN, ["task_001"])
