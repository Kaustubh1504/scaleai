import time

import pytest

from problem_api import make_api, task_id


def ids_range(a, b):
    return [task_id(i) for i in range(a, b + 1)]


def test_returns_records_in_input_order(sol):
    """Returns one record per id, in input order (responses finish out of order)"""
    api = make_api(n_tasks=50, latency_s=0.01)
    wanted = list(reversed(ids_range(1, 30)))
    rows = sol.enrich(api.client(), wanted, max_workers=8)
    assert [r["id"] for r in rows] == wanted, "results must follow input order, not completion order"


def test_records_are_the_api_bodies(sol):
    """Each record is the task's JSON body"""
    api = make_api(n_tasks=20, latency_s=0.005)
    rows = sol.enrich(api.client(), ids_range(1, 10), max_workers=4)
    assert rows == [api.tasks[t] for t in ids_range(1, 10)], "records should be the JSON bodies unchanged"


def test_one_request_per_id(sol):
    """Makes exactly one request per id"""
    api = make_api(n_tasks=40, latency_s=0.005)
    sol.enrich(api.client(), ids_range(1, 40), max_workers=8)
    paths = sorted(c.path for c in api.log)
    assert paths == sorted(f"/v1/tasks/{t}" for t in ids_range(1, 40)), "each task should be fetched exactly once"


def test_runs_in_parallel(sol):
    """200 tasks with 8 workers run in parallel: well under the ~4s serial time"""
    api = make_api(n_tasks=200, latency_s=0.02)
    started = time.perf_counter()
    rows = sol.enrich(api.client(), ids_range(1, 200), max_workers=8)
    elapsed = time.perf_counter() - started
    assert len(rows) == 200
    assert api.max_in_flight > 1, "requests never overlapped: are you waiting for each future before submitting the next?"
    assert elapsed < 2.0, f"took {elapsed:.2f}s; serial is ~4s, 8 workers should take ~0.5s"


def test_never_exceeds_max_workers(sol):
    """Never has more than max_workers requests in flight"""
    api = make_api(n_tasks=40, latency_s=0.01)
    sol.enrich(api.client(), ids_range(1, 40), max_workers=3)
    assert 1 < api.max_in_flight <= 3, f"max_workers=3 but max in flight was {api.max_in_flight}"


def test_single_worker_is_serial(sol):
    """max_workers=1 runs one request at a time"""
    api = make_api(n_tasks=10, latency_s=0.005)
    rows = sol.enrich(api.client(), ids_range(1, 6), max_workers=1)
    assert len(rows) == 6
    assert api.max_in_flight == 1


def test_duplicates_fetched_once(sol):
    """Duplicate ids are fetched once but appear at every input position"""
    api = make_api(n_tasks=10, latency_s=0.005)
    wanted = ["task_0003", "task_0001", "task_0003", "task_0002", "task_0001"]
    rows = sol.enrich(api.client(), wanted, max_workers=4)
    assert [r["id"] for r in rows] == wanted
    assert len(api.log) == 3, f"3 distinct ids should mean 3 requests, made {len(api.log)}"


def test_empty_input(sol):
    """An empty list returns [] without any request"""
    api = make_api(n_tasks=5)
    assert sol.enrich(api.client(), [], max_workers=4) == []
    assert api.log == []


def test_bad_max_workers(sol):
    """max_workers < 1 raises ValueError"""
    api = make_api(n_tasks=5)
    with pytest.raises(ValueError):
        sol.enrich(api.client(), ids_range(1, 3), max_workers=0)


def test_not_found_raises_api_error(sol):
    """A 404 for one id raises ApiError with status 404 and that task_id"""
    api = make_api(n_tasks=10, latency_s=0.005)
    with pytest.raises(sol.ApiError) as exc:
        sol.enrich(api.client(), ["task_0001", "task_9999", "task_0002"], max_workers=3)
    assert exc.value.status == 404
    assert exc.value.task_id == "task_9999"
