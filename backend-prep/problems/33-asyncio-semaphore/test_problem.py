import asyncio
import inspect
import time

import pytest

from problem_api import make_api, response_id


def ids_range(a, b):
    return [response_id(i) for i in range(a, b + 1)]


def run(sol, api, ids, limit):
    async def main():
        async with api.async_client() as client:
            return await sol.fetch_all(client, ids, limit=limit)

    return asyncio.run(main())


def test_is_coroutine_function(sol):
    """fetch_all is an async def"""
    assert inspect.iscoroutinefunction(sol.fetch_all), "fetch_all must be defined with `async def`"


def test_input_order_preserved(sol):
    """Returns the bodies in input order even though responses finish out of order"""
    api = make_api(n_responses=40, latency_s=0.01)
    wanted = list(reversed(ids_range(1, 24)))
    rows = run(sol, api, wanted, limit=6)
    assert [r["id"] for r in rows] == wanted, "results must follow input order, not completion order"
    assert rows[0] == api.records[wanted[0]], "records should be the JSON bodies unchanged"


def test_reaches_but_never_exceeds_limit(sol):
    """With 30 ids and limit=5, exactly 5 requests are in flight at peak"""
    api = make_api(n_responses=30, latency_s=0.01)
    run(sol, api, ids_range(1, 30), limit=5)
    assert api.max_in_flight <= 5, f"limit=5 but {api.max_in_flight} requests overlapped"
    assert api.max_in_flight == 5, f"peak concurrency was only {api.max_in_flight}; requests should fan out up to the limit"


def test_limit_one_is_serial(sol):
    """limit=1 makes one request at a time"""
    api = make_api(n_responses=10, latency_s=0.005)
    rows = run(sol, api, ids_range(1, 5), limit=1)
    assert len(rows) == 5
    assert api.max_in_flight == 1


def test_limit_above_count(sol):
    """A limit larger than the number of ids runs them all at once"""
    api = make_api(n_responses=10, latency_s=0.01)
    run(sol, api, ids_range(1, 4), limit=50)
    assert api.max_in_flight == 4


def test_faster_than_serial(sol):
    """60 requests with limit=10 take far less than the serial time"""
    api = make_api(n_responses=60, latency_s=0.02)
    started = time.perf_counter()
    rows = run(sol, api, ids_range(1, 60), limit=10)
    elapsed = time.perf_counter() - started
    assert len(rows) == 60 and len(api.log) == 60, "expected one request per id"
    assert elapsed < 0.6, f"took {elapsed:.2f}s; serial is ~1.2s, limit=10 should take ~0.15s"


def test_empty_input(sol):
    """An empty list returns [] without any request"""
    api = make_api(n_responses=5)
    assert run(sol, api, [], limit=3) == []
    assert api.log == []


def test_bad_limit(sol):
    """limit < 1 raises ValueError"""
    api = make_api(n_responses=5)
    with pytest.raises(ValueError):
        run(sol, api, ids_range(1, 3), limit=0)


def test_not_found_raises_api_error(sol):
    """A 404 raises ApiError with status 404 and that response_id"""
    api = make_api(n_responses=10, latency_s=0.005)
    with pytest.raises(sol.ApiError) as exc:
        run(sol, api, ["resp_0001", "resp_9999", "resp_0002"], limit=3)
    assert exc.value.status == 404
    assert exc.value.response_id == "resp_9999"


def test_works_across_event_loops(sol):
    """Can be called again in a fresh event loop (no module-level semaphore)"""
    for _ in range(2):
        api = make_api(n_responses=12, latency_s=0.005)
        rows = run(sol, api, ids_range(1, 12), limit=3)
        assert len(rows) == 12
        assert api.max_in_flight <= 3
