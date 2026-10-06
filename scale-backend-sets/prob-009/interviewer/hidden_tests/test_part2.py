"""Part 2: retries with backoff, 429 handling, per-project failure isolation."""

from pathlib import Path

import httpx
import pytest

from conftest import (API_KEY, PROJECTS, START, assert_complete, build_api, make_exporter, read_manifest, run_export,
                      tasks_requests)
from shared.fake_clock import FakeClock
from shared.mock_rest import FaultConfig, RateLimitConfig


def jsonl_files(out_dir):
    return sorted(p.name for p in Path(out_dir).glob("*.jsonl"))


def assert_failed(entry):
    assert set(entry) == {"status", "error"} and entry["status"] == "failed"
    assert isinstance(entry["error"], str) and entry["error"].strip()


def test_transient_5xx_retried_with_exponential_backoff(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_02/tasks?cursor": [503, 504]}))
    summary = run_export(api, clock, out)
    assert summary.ok
    assert_complete(api, out, "prj_02", read_manifest(out)["projects"]["prj_02"])
    assert len(clock.sleeps) == 2
    assert 1 <= clock.sleeps[0] <= 2 and 2 <= clock.sleeps[1] <= 3


def test_jitter_is_random(clock, out):
    scripted = {f"GET /v1/projects/{p}/tasks?limit": [502] for p in PROJECTS}
    api = build_api(clock, faults=FaultConfig(scripted=scripted))
    assert run_export(api, clock, out).ok
    assert len(clock.sleeps) == 8 and all(1 <= s <= 2 for s in clock.sleeps)
    assert len(set(clock.sleeps)) > 1


def test_gives_up_after_five_attempts_and_continues(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_03/tasks": [500] * 6}))
    summary = run_export(api, clock, out)
    manifest = read_manifest(out)
    assert_failed(manifest["projects"]["prj_03"])
    assert summary.projects["prj_03"]["status"] == "failed" and summary.ok is False
    assert [e.status for e in tasks_requests(api, "prj_03")] == [500] * 5
    assert len(clock.sleeps) == 4
    assert all(2 ** i <= s <= 2 ** i + 1 for i, s in enumerate(clock.sleeps))
    for project_id in PROJECTS:
        if project_id != "prj_03":
            assert_complete(api, out, project_id, manifest["projects"][project_id])
    assert "prj_03.jsonl" not in jsonl_files(out)


def test_failure_after_some_pages_leaves_no_file(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_04/tasks?cursor": [503] * 5}))
    run_export(api, clock, out)
    manifest = read_manifest(out)
    assert_failed(manifest["projects"]["prj_04"])
    assert tasks_requests(api, "prj_04")[0].status == 200  # the first page had been fetched
    assert jsonl_files(out) == [f"{p}.jsonl" for p in PROJECTS if p != "prj_04"]


def test_file_exists_only_for_complete_projects(clock, out):
    out.mkdir(parents=True)
    for stale in ("prj_99", "prj_03"):
        Path(out, f"{stale}.jsonl").write_text('{"stale": true}\n')
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_03/tasks": [500] * 5}))
    run_export(api, clock, out, ["prj_01", "prj_03", "prj_99"])
    assert jsonl_files(out) == ["prj_01.jsonl"]


def test_malformed_body_and_timeout_are_transient(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_05/tasks?limit": ["malformed", "timeout"]}))
    assert run_export(api, clock, out).ok
    assert [e.outcome for e in tasks_requests(api, "prj_05")][:3] == ["fault:malformed", "timeout", "ok"]
    assert_complete(api, out, "prj_05", read_manifest(out)["projects"]["prj_05"])


def test_connection_errors_are_transient(clock, out):
    seen = {"n": 0}

    def refuse_twice(api_, request):
        if "/prj_06/" in request.url.path:
            seen["n"] += 1
            if seen["n"] <= 2:
                raise httpx.ConnectError("connection refused", request=request)

    api = build_api(clock, on_request=refuse_twice)
    assert run_export(api, clock, out).ok
    assert len(clock.sleeps) == 2
    assert_complete(api, out, "prj_06", read_manifest(out)["projects"]["prj_06"])


def test_401_and_other_4xx_are_not_retried(clock, out):
    from exporter.client import ApiError, AuthError

    api = build_api(clock)
    with pytest.raises(AuthError):
        make_exporter(api, clock, out, api_key="wrong").export(PROJECTS)
    assert len(api.log) == 1
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_02/tasks": [400] * 5}))
    with pytest.raises(ApiError):
        run_export(api, clock, out)
    assert len(tasks_requests(api, "prj_02")) == 1 and clock.sleeps == []


def test_retry_after_seconds_is_honoured_exactly(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_01/tasks?limit": ["429:7", "429:3"]}))
    assert run_export(api, clock, out, ["prj_01"]).ok
    assert clock.sleeps == [7.0, 3.0]
    times = [e.at for e in tasks_requests(api, "prj_01")]
    assert times[1] - times[0] >= 7 and times[2] - times[1] >= 3


def test_429_without_retry_after_waits_until_reset(clock, out):
    # No Retry-After header; X-RateLimit-Reset is 5 s ahead (the window started with this request).
    api = build_api(clock, rate_limit=RateLimitConfig(requests=1000, window_s=5, retry_after_format="none"),
                    faults=FaultConfig(scripted={"GET /v1/projects/prj_01/tasks?limit": ["429:3"]}))
    assert run_export(api, clock, out, ["prj_01"]).ok
    assert clock.sleeps == [5.0]


def test_429_without_any_header_waits_one_second(clock, out):
    api = build_api(clock, rate_limit=RateLimitConfig(requests=1000, window_s=5, retry_after_format="none",
                                                      headers=False),
                    faults=FaultConfig(scripted={"GET /v1/projects/prj_01/tasks?limit": ["429:3"]}))
    assert run_export(api, clock, out, ["prj_01"]).ok
    assert clock.sleeps == [1.0]


def test_429s_do_not_use_up_attempts(clock, out):
    outcomes = ["429:1", 503, "429:1", 503, "429:1", 503, "429:1", 503, "429:1"]
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_06/tasks?limit": outcomes}))
    assert run_export(api, clock, out).ok
    assert_complete(api, out, "prj_06", read_manifest(out)["projects"]["prj_06"])


def test_eight_consecutive_429s_fail_the_project(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_07/tasks": ["429:1"] * 12}))
    run_export(api, clock, out)
    manifest = read_manifest(out)
    assert_failed(manifest["projects"]["prj_07"])
    assert len(tasks_requests(api, "prj_07")) == 8
    assert_complete(api, out, "prj_08", manifest["projects"]["prj_08"])


def test_real_rate_limit_is_waited_out(clock, out):
    api = build_api(clock, rate_limit=RateLimitConfig(requests=5, window_s=10))
    assert run_export(api, clock, out).ok
    manifest = read_manifest(out)
    for project_id in PROJECTS:
        assert_complete(api, out, project_id, manifest["projects"][project_id])
    log = api.requests("/v1")
    for i, entry in enumerate(log):
        if entry.status == 429:
            assert log[i + 1].at >= entry.at + 1  # waited instead of hammering
    assert len([e for e in log if e.status == 429]) <= len([e for e in log if e.status == 200])


def test_cli_exit_code_2_when_a_project_failed(clock, tmp_path):
    from exporter.__main__ import main

    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_02/tasks": [503] * 5}))
    argv = ["--project", "prj_01", "--project", "prj_02", "--api-key", API_KEY, "--out", str(tmp_path / "x")]
    assert main(argv, http=api.client(), clock=clock) == 2
    assert jsonl_files(tmp_path / "x") == ["prj_01.jsonl"]


@pytest.mark.change
def test_retry_after_http_date_is_measured_against_the_date_header(out):
    clock = FakeClock(start=START + 0.5)  # Date header says 08:00:00; Retry-After says 08:00:08
    api = build_api(clock, rate_limit=RateLimitConfig(requests=1000, window_s=1, retry_after_format="http-date"),
                    faults=FaultConfig(scripted={"GET /v1/projects/prj_01/tasks?limit": ["429:7"]}))
    assert run_export(api, clock, out, ["prj_01"]).ok
    assert clock.sleeps == [8.0]


@pytest.mark.change
def test_http_date_retry_after_under_a_real_limit(clock, out):
    # No X-RateLimit-* headers, so the Retry-After date is the only signal.
    api = build_api(clock, rate_limit=RateLimitConfig(requests=5, window_s=10, retry_after_format="http-date",
                                                      headers=False))
    assert run_export(api, clock, out).ok
    assert any(e.status == 429 for e in api.log)
    manifest = read_manifest(out)
    for project_id in PROJECTS:
        assert_complete(api, out, project_id, manifest["projects"][project_id])
