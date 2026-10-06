import json
import random
from pathlib import Path

import httpx
import pytest

from exporter.__main__ import main
from exporter.client import ApiError, AuthError, RetriesExhausted, TasksClient
from exporter.export import Exporter
from exporter.files import atomic_writer, sha256_file
from mock_services.api import API_KEY, make_api
from mock_services.clock import FakeClock
from shared.mock_rest import FaultConfig, RateLimitConfig

START = 1_714_550_400


@pytest.fixture
def clock():
    return FakeClock(start=START)


def exporter_for(api, clock, out):
    return Exporter(api.client(), API_KEY, clock, out, rng=random.Random(0))


def rendered_for(api, project_id):
    return [r for c, r in zip(api.canonical("tasks"), api.rendered("tasks")) if c["project_id"] == project_id]


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


# ------------------------------------------------------------------ client


def test_retry_after_parsing(clock):
    c = TasksClient(httpx.Client(), API_KEY, clock)
    date = "Wed, 01 May 2024 08:00:00 GMT"
    make = lambda h: httpx.Response(429, headers=h)  # noqa: E731
    assert c._retry_after(make({"Retry-After": "7"})) == 7
    assert c._retry_after(make({"Retry-After": "Wed, 01 May 2024 08:00:09 GMT", "Date": date})) == 9
    assert c._retry_after(make({"X-RateLimit-Reset": str(START + 4)})) == 4
    assert c._retry_after(make({})) == 1.0
    assert c._retry_after(make({"Retry-After": "soon"})) == 1.0


def test_backoff_schedule_and_give_up(clock):
    api = make_api(clock=clock, faults=FaultConfig(scripted={"prj_01/tasks": [503] * 5}))
    client = TasksClient(api.client(), API_KEY, clock, rng=random.Random(1))
    with pytest.raises(RetriesExhausted) as exc:
        client.get("/v1/projects/prj_01/tasks")
    assert exc.value.status == 503
    assert [int(s) for s in clock.sleeps] == [1, 2, 4, 8]


def test_auth_and_client_errors_are_not_retried(clock):
    api = make_api(clock=clock, faults=FaultConfig(scripted={"prj_02/tasks": [400]}))
    with pytest.raises(AuthError):
        TasksClient(api.client(), "nope", clock).get("/v1/projects/prj_01/tasks")
    with pytest.raises(ApiError) as exc:
        TasksClient(api.client(), API_KEY, clock).get("/v1/projects/prj_02/tasks")
    assert exc.value.status == 400 and len(api.log) == 2 and clock.sleeps == []


def test_429_cap(clock):
    api = make_api(clock=clock, faults=FaultConfig(scripted={"prj_01/tasks": ["429:2"] * 9}))
    with pytest.raises(RetriesExhausted):
        TasksClient(api.client(), API_KEY, clock).get("/v1/projects/prj_01/tasks")
    assert len(api.log) == 8 and clock.sleeps == [2.0] * 7


def test_throttle_avoids_the_limiter(clock):
    api = make_api(clock=clock, rate_limit=RateLimitConfig(requests=3, window_s=10))
    client = TasksClient(api.client(), API_KEY, clock)
    for _ in range(7):
        client.get("/v1/projects/prj_01/tasks")
    assert [e.status for e in api.log] == [200] * 7
    assert clock.sleeps == [10.0, 10.0]


# ------------------------------------------------------------------ files


def test_atomic_writer_leaves_old_file_on_error(tmp_path):
    target = tmp_path / "a.jsonl"
    target.write_bytes(b"old\n")
    with pytest.raises(RuntimeError):
        with atomic_writer(target) as fh:
            fh.write(b"partial")
            raise RuntimeError("boom")
    assert target.read_bytes() == b"old\n" and [p.name for p in tmp_path.iterdir()] == ["a.jsonl"]
    assert sha256_file(tmp_path / "missing") is None


# ------------------------------------------------------------------ export


def test_export_writes_files_and_manifest(clock, tmp_path):
    api = make_api(clock=clock)
    summary = exporter_for(api, clock, tmp_path).export(["prj_02", "prj_99", "prj_01"])
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest == {"generated_at": "2024-05-01T08:00:00Z", "projects": summary.projects}
    assert list(summary.projects) == ["prj_02", "prj_99", "prj_01"]
    assert summary.projects["prj_99"] == {"status": "not_found"} and not summary.ok
    for pid in ("prj_01", "prj_02"):
        assert lines(tmp_path / f"{pid}.jsonl") == rendered_for(api, pid)
        assert summary.projects[pid]["sha256"] == sha256_file(tmp_path / f"{pid}.jsonl")


def test_failed_project_is_isolated(clock, tmp_path):
    api = make_api(clock=clock, faults=FaultConfig(scripted={"prj_02/tasks?cursor": [502] * 5}))
    summary = exporter_for(api, clock, tmp_path).export(["prj_01", "prj_02", "prj_03"])
    assert [e["status"] for e in summary.projects.values()] == ["complete", "failed", "complete"]
    assert "502" in summary.projects["prj_02"]["error"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["manifest.json", "prj_01.jsonl", "prj_03.jsonl"]


def test_rejects_unsafe_ids(clock, tmp_path):
    with pytest.raises(ValueError):
        exporter_for(make_api(clock=clock), clock, tmp_path).export(["../../etc/passwd"])


def test_resume_skips_verified_files_only(clock, tmp_path):
    exporter_for(make_api(clock=clock), clock, tmp_path).export(["prj_01", "prj_02"])
    (tmp_path / "prj_02.jsonl").write_text("tampered\n")
    api = make_api(clock=clock)
    summary = exporter_for(api, clock, tmp_path).export(["prj_01", "prj_02"])
    assert {e.path for e in api.log} == {"/v1/projects/prj_02/tasks"}
    assert lines(tmp_path / "prj_02.jsonl") == rendered_for(api, "prj_02") and summary.ok


def test_crash_keeps_previous_manifest(clock, tmp_path):
    exporter_for(make_api(clock=clock), clock, tmp_path).export(["prj_01"])
    before = (tmp_path / "manifest.json").read_bytes()

    def crash(api_, request):
        if "cursor" in request.url.params:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        exporter_for(make_api(clock=clock, on_request=crash), clock, tmp_path).export(["prj_02"])
    assert (tmp_path / "manifest.json").read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["manifest.json", "prj_01.jsonl"]


def test_full_crawl_under_limit_and_faults(clock, tmp_path):
    api = make_api(clock=clock, rate_limit=RateLimitConfig(requests=5, window_s=10),
                   faults=FaultConfig(seed=3, failure_rate=0.2, malformed_rate=0.1))
    summary = exporter_for(api, clock, tmp_path).export([f"prj_{i:02d}" for i in range(1, 9)])
    assert summary.ok and not [e for e in api.log if e.outcome == "rate_limited"]
    assert sum(s["tasks"] for s in summary.projects.values()) == 400


def test_cli_exit_codes(clock, tmp_path):
    ok = make_api(clock=clock)
    assert main(["--project", "prj_01", "--out", str(tmp_path / "a")], http=ok.client(), clock=clock) == 0
    flaky = make_api(clock=clock, faults=FaultConfig(scripted={"prj_01/tasks": [500] * 5}))
    assert main(["--project", "prj_01", "--out", str(tmp_path / "b")], http=flaky.client(), clock=clock) == 2
    assert main(["--project", "prj_01", "--api-key", "x", "--out", str(tmp_path / "c")], http=ok.client(),
                clock=clock) == 1
