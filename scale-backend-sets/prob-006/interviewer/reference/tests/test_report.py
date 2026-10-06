import json
import random
from datetime import datetime

import httpx
import pytest

from mock_services.api import CLIENT_ID, CLIENT_SECRET, make_api
from mock_services.clock import FakeClock
from report.__main__ import main
from report.client import ApiClient, ApiError, AuthError
from report.report import build_report, summarize_project
from shared.mock_rest import FaultConfig, RateLimitConfig


@pytest.fixture
def clock():
    return FakeClock(start=1_714_550_400)


def client_for(api, clock, **kwargs):
    return ApiClient(api.client(), CLIENT_ID, CLIENT_SECRET, clock, rng=random.Random(0), **kwargs)


def task(status, created="2024-04-01T00:00:00Z", completed=None):
    return {"status": status, "created_at": created, "completed_at": completed}


def test_summarize_project_math():
    project = {"id": "p", "name": "n", "customer": {"id": "c"}, "status": "active"}
    tasks = [task("completed", completed="2024-04-01T00:10:00Z"), task("completed", completed="2024-04-01T00:15:00Z"),
             task("pending"), task("rejected")]
    row = summarize_project(project, tasks)
    assert (row["tasks_total"], row["tasks_completed"], row["completion_rate"]) == (4, 2, 0.5)
    assert row["median_minutes_to_complete"] == 12.5
    assert row["tasks_by_status"] == {"pending": 1, "in_progress": 0, "completed": 2, "rejected": 1}
    assert summarize_project(project, [])["completion_rate"] is None


def test_report_counts_everything(clock):
    api = make_api(clock=clock)
    report = build_report(client_for(api, clock))
    assert report["totals"] == {"projects": 12, "tasks_total": 600,
                                "tasks_completed": sum(t["status"] == "completed" for t in api.canonical("tasks"))}
    assert report["generated_at"] == "2024-05-01T08:00:00Z"
    assert sum(c["projects"] for c in report["customers"]) == 12


def test_proactive_refresh_uses_refresh_tokens(clock):
    api = make_api(clock=clock, token_ttl_s=10, latency_s=1.0)
    build_report(client_for(api, clock))
    assert not [e for e in api.requests("/v1") if e.status == 401]
    assert api.tokens_issued > 3


def test_revocation_is_retried_once(clock):
    api = make_api(clock=clock)
    c = client_for(api, clock)
    c.get("/v1/projects")
    api.expire_all_tokens()
    assert c.get("/v1/projects")["page"] == 1
    assert [e.status for e in api.requests("/v1")] == [200, 401, 200]


def test_bad_secret(clock):
    api = make_api(clock=clock)
    with pytest.raises(AuthError):
        ApiClient(api.client(), CLIENT_ID, "nope", clock).get("/v1/projects")


def test_retry_after_parsing(clock):
    c = client_for(make_api(clock=clock), clock)
    date = "Wed, 01 May 2024 08:00:00 GMT"
    make = lambda h: httpx.Response(429, headers=h)  # noqa: E731
    assert c._retry_after(make({"Retry-After": "7"})) == 7
    assert c._retry_after(make({"Retry-After": "Wed, 01 May 2024 08:00:09 GMT", "Date": date})) == 9
    assert c._retry_after(make({})) == 1.0
    assert c._retry_after(make({"Retry-After": "soon"})) == 1.0


def test_backoff_and_give_up(clock):
    api = make_api(clock=clock, faults=FaultConfig(scripted={"GET /v1/projects": [503] * 4}))
    with pytest.raises(ApiError) as exc:
        client_for(api, clock).get("/v1/projects")
    assert exc.value.status == 503
    assert len(clock.sleeps) == 3 and clock.sleeps[2] <= 2.0


def test_rate_limit_end_to_end(clock):
    api = make_api(clock=clock, rate_limit=RateLimitConfig(requests=3, window_s=5, retry_after_format="http-date"))
    report = build_report(client_for(api, clock))
    assert report["totals"]["tasks_total"] == 600
    assert any(e.status == 429 for e in api.log)


def test_cli_writes_report(tmp_path):
    api = make_api(clock=FakeClock())
    out = tmp_path / "r.json"
    assert main(["--out", str(out)], http=api.client()) == 0
    assert json.loads(out.read_text())["totals"]["projects"] == 12
    broken = make_api(faults=FaultConfig(scripted={"GET /v1/projects": [404]}))
    assert main(["--out", str(tmp_path / "x.json")], http=broken.client()) == 1


def test_generated_at_parses(clock):
    report = build_report(client_for(make_api(clock=clock), clock))
    assert datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00")).timestamp() == 1_714_550_400
