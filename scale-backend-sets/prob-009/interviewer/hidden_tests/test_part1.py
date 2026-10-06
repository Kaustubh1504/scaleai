"""Part 1: crawl each project, write JSONL files and the manifest."""

from pathlib import Path

import pytest

from conftest import (API_KEY, PROJECTS, assert_complete, build_api, expected_pages, expected_records, make_exporter,
                      read_manifest, result_files, run_export, sha256, tasks_requests)
from shared.mock_rest import FaultConfig


def test_every_project_file_matches_the_api(clock, out):
    api = build_api(clock)
    summary = run_export(api, clock, out)
    manifest = read_manifest(out)
    assert list(manifest["projects"]) == PROJECTS
    for project_id in PROJECTS:
        assert_complete(api, out, project_id, manifest["projects"][project_id])
    assert summary.projects == manifest["projects"]


def test_records_are_written_exactly_as_received(clock, out):
    api = build_api(clock)
    run_export(api, clock, out, ["prj_03"])
    clean = [t for t in api.canonical("tasks") if t["project_id"] == "prj_03"]
    shown = expected_records(api, "prj_03")
    assert clean != shown  # this project has inconsistently typed fields on the wire
    lines = Path(out, "prj_03.jsonl").read_text().splitlines()
    assert len(lines) == len(shown) and all(line.strip() for line in lines)


def test_manifest_order_generated_at_and_summary(clock, out):
    api = build_api(clock)
    order = ["prj_05", "prj_01", "prj_08"]
    summary = run_export(api, clock, out, order)
    manifest = read_manifest(out)
    assert set(manifest) == {"generated_at", "projects"}
    assert list(manifest["projects"]) == order
    assert manifest["generated_at"] == summary.generated_at == "2024-05-01T08:00:00Z"
    assert summary.ok is True
    assert [e.path for e in tasks_requests(api) if "cursor" not in e.params] == [
        f"/v1/projects/{p}/tasks" for p in order]


def test_lines_end_with_newline(clock, out):
    api = build_api(clock)
    run_export(api, clock, out, ["prj_02"])
    data = Path(out, "prj_02.jsonl").read_bytes()
    assert data.endswith(b"\n") and not data.endswith(b"\n\n")


def test_each_page_fetched_once_with_limit_25(clock, out):
    api = build_api(clock)
    run_export(api, clock, out)
    gets = tasks_requests(api)
    assert len(gets) == expected_pages(api, PROJECTS)
    assert all(e.params.get("limit") == "25" for e in gets)
    keys = [(e.path, tuple(sorted(e.params.items()))) for e in gets]
    assert len(keys) == len(set(keys))
    assert any(e.params.get("cursor") for e in gets)


def test_api_key_header_is_sent(clock, out):
    api = build_api(clock)
    run_export(api, clock, out, ["prj_01"])
    assert api.log and all(e.status != 401 and e.identity == API_KEY for e in api.log)


def test_unknown_project_is_not_found_without_a_file(clock, out):
    api = build_api(clock)
    summary = run_export(api, clock, out, ["prj_01", "prj_99", "prj_02"])
    manifest = read_manifest(out)
    assert manifest["projects"]["prj_99"] == {"status": "not_found"}
    assert not Path(out, "prj_99.jsonl").exists()
    assert_complete(api, out, "prj_02", manifest["projects"]["prj_02"])
    assert summary.ok is False


def test_project_without_tasks_gets_an_empty_file(clock, out):
    api = build_api(clock, tasks=3)
    empty = next(p for p in PROJECTS if not expected_records(api, p))
    run_export(api, clock, out, [empty])
    entry = read_manifest(out)["projects"][empty]
    assert Path(out, f"{empty}.jsonl").read_bytes() == b""
    assert entry == {"status": "complete", "tasks": 0, "file": f"{empty}.jsonl", "sha256": sha256(Path(out, f"{empty}.jsonl"))}


def test_out_dir_is_created(clock, tmp_path):
    api = build_api(clock)
    nested = tmp_path / "a" / "b" / "exports"
    run_export(api, clock, nested, ["prj_01"])
    assert (nested / "manifest.json").exists() and (nested / "prj_01.jsonl").exists()


def test_bad_api_key_raises_auth_error_and_writes_no_manifest(clock, out):
    from exporter.client import ApiError, AuthError

    api = build_api(clock)
    with pytest.raises(AuthError) as exc:
        make_exporter(api, clock, out, api_key="wrong").export(["prj_01"])
    assert isinstance(exc.value, ApiError) and exc.value.status == 401
    assert not Path(out, "manifest.json").exists()


def test_other_4xx_raises_api_error_with_status_and_path(clock, out):
    from exporter.client import ApiError

    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_03/tasks": [403] * 10}))
    with pytest.raises(ApiError) as exc:
        run_export(api, clock, out)
    assert exc.value.status == 403 and "prj_03" in (exc.value.path or "")


@pytest.mark.parametrize("bad", ["../etc", "prj 01", "a/b", ""])
def test_unsafe_project_id_rejected_before_any_request(clock, out, bad):
    api = build_api(clock)
    with pytest.raises(ValueError):
        run_export(api, clock, out, ["prj_01", bad])
    assert api.log == []


def test_cli_exit_codes(clock, tmp_path):
    from exporter.__main__ import main

    api = build_api(clock)
    ok = ["--project", "prj_01", "--project", "prj_02", "--api-key", API_KEY]
    assert main([*ok, "--out", str(tmp_path / "a")], http=api.client(), clock=clock) == 0
    assert result_files(tmp_path / "a") == ["manifest.json", "prj_01.jsonl", "prj_02.jsonl"]
    assert main([*ok, "--project", "prj_99", "--out", str(tmp_path / "b")], http=api.client(), clock=clock) == 2
    assert main(["--project", "prj_01", "--api-key", "wrong", "--out", str(tmp_path / "c")], http=api.client(), clock=clock) == 1
