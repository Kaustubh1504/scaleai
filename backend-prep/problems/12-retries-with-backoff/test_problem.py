import random

import pytest

from problem_api import make_api

PATH = "/v1/tasks/task_001"
KEY = f"GET {PATH}"


def expected_sleeps(n_sleeps, seed, base_s=0.5, cap_s=8.0):
    rng = random.Random(seed)
    out = []
    for attempt in range(1, n_sleeps + 1):
        d = min(cap_s, base_s * 2 ** (attempt - 1))
        out.append(rng.uniform(d / 2, d))
    return out


def call(sol, api, clock, seed=0, method="GET", path=PATH, **kwargs):
    return sol.request_with_retries(api.client(), method, path, clock=clock, rng=random.Random(seed), **kwargs)


def test_success_first_try(sol, clock):
    """A healthy endpoint returns the response after one request and never sleeps"""
    api = make_api()
    resp = call(sol, api, clock)
    assert resp.status_code == 200
    assert resp.json()["id"] == "task_001"
    assert len(api.log) == 1, f"expected 1 request, made {len(api.log)}"
    assert clock.sleeps == [], "don't sleep before the first attempt or after a success"


def test_retries_503_then_succeeds(sol, clock):
    """Two 503s then success: 3 requests, 2 sleeps drawn from rng.uniform(d/2, d)"""
    api = make_api()
    api.script(KEY, [503, 503])
    resp = call(sol, api, clock, seed=42)
    assert resp.json()["id"] == "task_001"
    assert len(api.log) == 3, f"expected 3 requests, made {len(api.log)}"
    assert len(clock.sleeps) == 2, f"expected exactly 2 sleeps, got {clock.sleeps}"
    assert 0.25 <= clock.sleeps[0] <= 0.5, f"first sleep must be in [0.25, 0.5], got {clock.sleeps[0]}"
    assert 0.5 <= clock.sleeps[1] <= 1.0, f"second sleep must be in [0.5, 1.0], got {clock.sleeps[1]}"
    assert clock.sleeps == pytest.approx(expected_sleeps(2, 42)), \
        "call rng.uniform(d / 2, d) exactly once per sleep, and use rng for nothing else"


def test_every_transient_kind_is_retried(sol, clock):
    """500, 502, 504, timeout, connect error and a truncated 200 body are all retried"""
    api = make_api()
    api.script(KEY, [500, 502, 504, "timeout", "connect", "malformed"])
    resp = call(sol, api, clock, max_attempts=7)
    assert resp.json()["id"] == "task_001", "the final, valid response should be returned"
    assert len(api.log) == 7, f"expected 7 requests (6 faults + 1 success), made {len(api.log)}"
    assert len(clock.sleeps) == 6


def test_exhausted_raises_with_last_status(sol, clock):
    """Four 503s raise ApiError(503, attempts=4) after 3 sleeps (none after the last attempt)"""
    api = make_api()
    api.script(KEY, [503, 503, 503, 503, "pass"])
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api, clock, seed=1)
    assert exc.value.status == 503
    assert exc.value.attempts == 4
    assert exc.value.path == PATH
    assert len(api.log) == 4, f"max_attempts=4 means 4 requests, made {len(api.log)}"
    assert clock.sleeps == pytest.approx(expected_sleeps(3, 1)), "3 sleeps between 4 attempts, none after the last"


def test_exhausted_on_transport_error_has_status_none(sol, clock):
    """If the last attempt was a transport error, ApiError.status is None"""
    api = make_api()
    api.script(KEY, [503, "timeout", "connect"])
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api, clock, max_attempts=3)
    assert exc.value.status is None, f"last attempt raised ConnectError, status should be None, got {exc.value.status}"
    assert exc.value.attempts == 3


def test_exhausted_on_garbage_body_has_status_200(sol, clock):
    """If every response is a truncated 200, ApiError carries status 200"""
    api = make_api()
    api.script(KEY, ["malformed", "malformed"])
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api, clock, max_attempts=2)
    assert exc.value.status == 200
    assert exc.value.attempts == 2
    assert len(clock.sleeps) == 1


def test_404_not_retried(sol, clock):
    """A 404 raises ApiError(404, attempts=1) immediately: no retry, no sleep"""
    api = make_api()
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api, clock, path="/v1/tasks/task_999")
    assert exc.value.status == 404
    assert exc.value.attempts == 1
    assert len(api.log) == 1, "a 404 will be a 404 next time too: don't retry it"
    assert clock.sleeps == []


def test_fatal_after_transient(sol, clock):
    """A 503 followed by a 422 stops at the 422 with attempts=2"""
    api = make_api()
    api.script("POST /v1/tasks/task_001/labels", [503])
    with pytest.raises(sol.ApiError) as exc:
        call(sol, api, clock, method="POST", path="/v1/tasks/task_001/labels", json={})
    assert exc.value.status == 422
    assert exc.value.attempts == 2
    assert len(api.log) == 2
    assert len(clock.sleeps) == 1, "one sleep between the 503 and the 422, none after the 422"


def test_backoff_is_capped(sol, clock):
    """Delays double from base_s and stop growing at cap_s"""
    api = make_api()
    api.script(KEY, [503] * 7)
    call(sol, api, clock, seed=7, max_attempts=8, base_s=0.5, cap_s=2.0)
    ceilings = [0.5, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0]
    assert len(clock.sleeps) == 7
    for i, (slept, d) in enumerate(zip(clock.sleeps, ceilings), start=1):
        assert d / 2 <= slept <= d, f"sleep after attempt {i} should be in [{d / 2}, {d}], got {slept}"
    assert clock.sleeps == pytest.approx(expected_sleeps(7, 7, cap_s=2.0))


def test_forwards_kwargs(sol, clock):
    """method, json= and headers= reach the server unchanged, including on retries"""
    api = make_api()
    path = "/v1/tasks/task_002/labels"
    api.script(f"POST {path}", ["timeout"])
    resp = call(sol, api, clock, method="POST", path=path, json={"label": "cat"},
                headers={"X-Request-Source": "pipeline"})
    assert resp.status_code == 201
    calls = api.calls("POST", path)
    assert len(calls) == 2
    for c in calls:
        assert c.json() == {"label": "cat"}, "json= must be passed through"
        assert c.header("x-request-source") == "pipeline", "headers= must be passed through"
