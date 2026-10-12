import pytest

from problem_api import doc_id, make_api


def ids_range(a, b):
    return [doc_id(i) for i in range(a, b + 1)]


def path(did):
    return f"/v1/documents/{did}"


def by_id(failures):
    return {f["id"]: f for f in failures}


def test_all_succeed(sol):
    """All documents succeed: results hold id/title/pages only, failures is empty"""
    api = make_api(n_docs=10)
    out = sol.fetch_documents(api.client(), ids_range(1, 10))
    assert out["failures"] == []
    assert set(out["results"]) == set(ids_range(1, 10))
    d = api.docs["doc_003"]
    assert out["results"]["doc_003"] == {"id": "doc_003", "title": d["title"], "pages": d["pages"]}, \
        "each result should keep only id, title and pages"


def test_not_found(sol):
    """A 404 becomes a not_found failure and the rest still succeed"""
    api = make_api(n_docs=5)
    out = sol.fetch_documents(api.client(), ["doc_001", "doc_999", "doc_002"])
    assert set(out["results"]) == {"doc_001", "doc_002"}
    assert [f["id"] for f in out["failures"]] == ["doc_999"]
    assert out["failures"][0]["error_type"] == "not_found"
    assert len(api.calls("GET", path("doc_999"))) == 1, "404s must not be retried"


def test_server_error_retried_once_then_fails(sol):
    """Two 5xx in a row: exactly 2 requests, then a server_error failure"""
    api = make_api(n_docs=5)
    api.script(f"GET {path('doc_002')}", [500, 503])
    out = sol.fetch_documents(api.client(), ids_range(1, 4))
    assert by_id(out["failures"])["doc_002"]["error_type"] == "server_error"
    assert len(api.calls("GET", path("doc_002"))) == 2, "a 5xx is retried exactly once"
    assert set(out["results"]) == {"doc_001", "doc_003", "doc_004"}


def test_server_error_recovers_on_retry(sol):
    """A 5xx followed by a 200 counts as a result, not a failure"""
    api = make_api(n_docs=5)
    api.script(f"GET {path('doc_003')}", [503])
    out = sol.fetch_documents(api.client(), ids_range(1, 5))
    assert out["failures"] == [], "the retry succeeded, so there's no failure"
    assert out["results"]["doc_003"]["id"] == "doc_003"
    assert len(api.calls("GET", path("doc_003"))) == 2


def test_timeout(sol):
    """A timeout becomes a timeout failure and is not retried"""
    api = make_api(n_docs=5)
    api.script(f"GET {path('doc_004')}", ["timeout"])
    out = sol.fetch_documents(api.client(), ids_range(1, 5))
    assert by_id(out["failures"])["doc_004"]["error_type"] == "timeout"
    assert len(api.calls("GET", path("doc_004"))) == 1, "timeouts are not retried in this problem"
    assert len(out["results"]) == 4


def test_other_errors(sol):
    """A 403 and a ConnectError are both 'other' failures"""
    api = make_api(n_docs=5)
    api.script(f"GET {path('doc_001')}", [403])
    api.script(f"GET {path('doc_005')}", ["connect"])
    out = sol.fetch_documents(api.client(), ids_range(1, 5))
    f = by_id(out["failures"])
    assert set(f) == {"doc_001", "doc_005"}
    assert f["doc_001"]["error_type"] == "other", "a non-404 4xx is 'other'"
    assert f["doc_005"]["error_type"] == "other", "a ConnectError is 'other'"
    assert len(api.calls("GET", path("doc_001"))) == 1, "4xx must not be retried"


def test_mixed_batch_shape_and_order(sol):
    """Mixed batch: failures sorted by id with exactly id/error_type/message, every id accounted for once"""
    api = make_api(n_docs=12)
    api.script(f"GET {path('doc_009')}", ["timeout"])
    api.script(f"GET {path('doc_002')}", [500, 500])
    api.script(f"GET {path('doc_006')}", [403])
    wanted = ids_range(1, 12) + ["doc_404"]
    out = sol.fetch_documents(api.client(), list(reversed(wanted)))
    failures = out["failures"]
    assert [f["id"] for f in failures] == ["doc_002", "doc_006", "doc_009", "doc_404"], "failures must be sorted by id"
    assert [f["error_type"] for f in failures] == ["server_error", "other", "timeout", "not_found"]
    for f in failures:
        assert set(f) == {"id", "error_type", "message"}, f"unexpected failure keys: {sorted(f)}"
        assert isinstance(f["message"], str) and f["message"], "message must be a non-empty string"
    assert set(out["results"]) | {f["id"] for f in failures} == set(wanted)
    assert not set(out["results"]) & {f["id"] for f in failures}, "an id can't be both a result and a failure"


def test_failures_do_not_cancel_others(sol):
    """Early failures don't stop the batch: every id is requested"""
    api = make_api(n_docs=20)
    for did in ids_range(1, 4):
        api.script(f"GET {path(did)}", ["timeout"])
    out = sol.fetch_documents(api.client(), ids_range(1, 20), max_workers=2)
    requested = {c.path for c in api.log}
    assert requested == {path(d) for d in ids_range(1, 20)}, "some ids were never requested"
    assert len(out["results"]) == 16


def test_bug_propagates(sol):
    """A 200 record missing 'title' raises KeyError instead of becoming a failure"""
    api = make_api(n_docs=6, broken=("doc_004",))
    with pytest.raises(KeyError):
        sol.fetch_documents(api.client(), ids_range(1, 6))


def test_runs_concurrently(sol):
    """Requests overlap, but never more than max_workers at once"""
    api = make_api(n_docs=24, real_latency_s=0.01)
    out = sol.fetch_documents(api.client(), ids_range(1, 24), max_workers=4)
    assert len(out["results"]) == 24
    assert 1 < api.max_in_flight <= 4, f"max_workers=4 but max in flight was {api.max_in_flight}"


def test_empty_input(sol):
    """An empty list returns empty results and failures without any request"""
    api = make_api(n_docs=3)
    assert sol.fetch_documents(api.client(), []) == {"results": {}, "failures": []}
    assert api.log == []
