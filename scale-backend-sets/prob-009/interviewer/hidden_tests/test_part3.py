"""Part 3: atomic writes, crash safety, resume, proactive throttling."""

import os
from pathlib import Path

import pytest

from conftest import (PROJECTS, START, assert_complete, build_api, expected_pages, read_manifest, result_files,
                      run_export, tasks_requests)
from shared.mock_rest import FaultConfig, RateLimitConfig


def snapshot(out_dir):
    """Bytes of every visible result file."""
    return {p.name: p.read_bytes() for p in Path(out_dir).iterdir() if not p.name.startswith(".")}


def assert_no_temp_files(out_dir):
    leftovers = [name for name in result_files(out_dir) if name.startswith(".") or name.endswith(".tmp")]
    assert leftovers == [], f"temporary files left behind: {leftovers}"


# ------------------------------------------------------------------ throttling


def test_proactive_throttling_gets_no_429s(clock, out):
    api = build_api(clock, rate_limit=RateLimitConfig(requests=4, window_s=10))
    assert run_export(api, clock, out).ok
    assert [e for e in api.log if e.outcome == "rate_limited"] == []
    manifest = read_manifest(out)
    for project_id in PROJECTS:
        assert_complete(api, out, project_id, manifest["projects"][project_id])


def test_throttle_waits_exactly_until_reset(clock, out):
    # 3 requests per 10 s: the 3rd response says Remaining 0, Reset = start + 10.
    api = build_api(clock, rate_limit=RateLimitConfig(requests=3, window_s=10))
    assert run_export(api, clock, out, ["prj_03", "prj_01"]).ok  # prj_03 has 3 pages
    gets = tasks_requests(api)
    assert [e.at for e in gets[:4]] == [START, START, START, START + 10]
    assert clock.sleeps[0] == 10.0
    assert [e for e in api.log if e.status == 429] == []


def test_throttling_also_follows_error_responses(clock, out):
    # The 3rd request of the window is a 503 that says Remaining 0: the retry must wait for the reset,
    # not just the 1-2 s back-off.
    api = build_api(clock, rate_limit=RateLimitConfig(requests=3, window_s=10),
                    faults=FaultConfig(scripted={"GET /v1/projects/prj_03/tasks?cursor": ["ok", 503]}))
    assert run_export(api, clock, out, ["prj_03"]).ok
    gets = tasks_requests(api)
    assert [e.status for e in gets] == [200, 200, 503, 200]
    assert gets[3].at >= START + 10
    assert_complete(api, out, "prj_03", read_manifest(out)["projects"]["prj_03"])


def test_throttling_under_random_faults(clock, out):
    api = build_api(clock, rate_limit=RateLimitConfig(requests=4, window_s=10),
                    faults=FaultConfig(failure_rate=0.25, malformed_rate=0.1))
    assert run_export(api, clock, out).ok
    assert any(e.outcome.startswith("fault:") for e in api.log)
    assert [e for e in api.log if e.outcome == "rate_limited"] == []


# ------------------------------------------------------------------ resume


def test_rerun_skips_complete_projects(clock, out):
    run_export(build_api(clock), clock, out)
    first = read_manifest(out)
    clock.advance(3600)
    api = build_api(clock)
    summary = run_export(api, clock, out)
    assert tasks_requests(api) == []
    manifest = read_manifest(out)
    assert manifest["projects"] == first["projects"] == summary.projects
    assert manifest["generated_at"] == "2024-05-01T09:00:00Z"


def test_rerun_reexports_modified_and_deleted_files(clock, out):
    run_export(build_api(clock), clock, out)
    with Path(out, "prj_02.jsonl").open("a") as fh:
        fh.write('{"id": "tsk_injected"}\n')
    Path(out, "prj_05.jsonl").unlink()
    api = build_api(clock)
    run_export(api, clock, out)
    assert sorted({e.path for e in tasks_requests(api)}) == ["/v1/projects/prj_02/tasks", "/v1/projects/prj_05/tasks"]
    manifest = read_manifest(out)
    for project_id in PROJECTS:
        assert_complete(api, out, project_id, manifest["projects"][project_id])


def test_rerun_retries_failed_and_not_found_projects(clock, out):
    ids = [*PROJECTS, "prj_99"]
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_03/tasks": [500] * 5}))
    run_export(api, clock, out, ids)
    assert read_manifest(out)["projects"]["prj_03"]["status"] == "failed"
    api = build_api(clock)
    assert run_export(api, clock, out, ids).projects["prj_99"] == {"status": "not_found"}
    assert sorted({e.path for e in tasks_requests(api)}) == ["/v1/projects/prj_03/tasks", "/v1/projects/prj_99/tasks"]
    assert_complete(api, out, "prj_03", read_manifest(out)["projects"]["prj_03"])


def test_rerun_with_a_different_project_list(clock, out):
    run_export(build_api(clock), clock, out, ["prj_01", "prj_02"])
    api = build_api(clock)
    run_export(api, clock, out, ["prj_02", "prj_03"])
    assert {e.path for e in tasks_requests(api)} == {"/v1/projects/prj_03/tasks"}
    manifest = read_manifest(out)
    assert list(manifest["projects"]) == ["prj_02", "prj_03"]
    assert_complete(api, out, "prj_02", manifest["projects"]["prj_02"])


def test_unreadable_manifest_means_full_export(clock, out):
    run_export(build_api(clock), clock, out)
    Path(out, "manifest.json").write_text('{"generated_at": "2024-05-01T08:00:00Z", "proj')
    api = build_api(clock)
    run_export(api, clock, out)
    assert len(tasks_requests(api)) == expected_pages(api, PROJECTS)
    assert read_manifest(out)["projects"]["prj_01"]["status"] == "complete"


# ------------------------------------------------------------------ crash safety


def test_crash_mid_project_keeps_previous_results(clock, out):
    run_export(build_api(clock), clock, out, ["prj_01", "prj_02"])
    before = snapshot(out)
    calls = {"n": 0}

    def crash_on_second_page(api_, request):
        if request.url.path == "/v1/projects/prj_04/tasks":
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("worker killed")

    api = build_api(clock, on_request=crash_on_second_page)
    with pytest.raises(RuntimeError):
        run_export(api, clock, out, ["prj_03", "prj_04"])
    after = snapshot(out)
    assert after["manifest.json"] == before["manifest.json"]
    assert after["prj_01.jsonl"] == before["prj_01.jsonl"] and after["prj_02.jsonl"] == before["prj_02.jsonl"]
    assert "prj_04.jsonl" not in after
    assert set(after) <= {"manifest.json", "prj_01.jsonl", "prj_02.jsonl", "prj_03.jsonl"}
    assert_no_temp_files(out)


def _failing_replace(monkeypatch, target_name):
    real = os.replace

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == target_name:
            raise OSError(28, "No space left on device")
        return real(src, dst, *args, **kwargs)

    def path_replace(self, target):  # Path.replace binds os.replace early on Python 3.10
        replace(self, target)
        return type(self)(target)

    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(Path, "replace", path_replace)


def test_failed_manifest_write_keeps_previous_manifest(clock, out, monkeypatch):
    run_export(build_api(clock), clock, out)
    before = snapshot(out)
    Path(out, "prj_02.jsonl").unlink()
    _failing_replace(monkeypatch, "manifest.json")
    with pytest.raises(OSError):
        run_export(build_api(clock), clock, out)
    assert snapshot(out)["manifest.json"] == before["manifest.json"]
    assert_no_temp_files(out)


def test_failed_file_write_keeps_previous_file(clock, out, monkeypatch):
    run_export(build_api(clock), clock, out)
    with Path(out, "prj_02.jsonl").open("a") as fh:
        fh.write('{"id": "tsk_injected"}\n')
    before = snapshot(out)
    _failing_replace(monkeypatch, "prj_02.jsonl")
    with pytest.raises(OSError):
        run_export(build_api(clock), clock, out)
    assert snapshot(out) == before
    assert_no_temp_files(out)


def test_failed_project_leaves_no_temp_files(clock, out):
    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_04/tasks?cursor": [503] * 5}))
    run_export(api, clock, out)
    assert result_files(out) == sorted(["manifest.json", *[f"{p}.jsonl" for p in PROJECTS if p != "prj_04"]])
