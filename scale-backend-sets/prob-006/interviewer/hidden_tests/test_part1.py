"""Part 1: auth, both pagination styles, aggregation."""

import pytest

from conftest import build_api, expected_projects, make_client, run_report, strip_change


def test_report_matches_oracle(clock):
    api = build_api(clock)
    report = run_report(api, clock)
    assert strip_change(report["projects"]) == strip_change(expected_projects(api))


def test_totals_and_generated_at(clock):
    api = build_api(clock)
    report = run_report(api, clock)
    rows = expected_projects(api)
    assert report["totals"] == {"projects": len(rows), "tasks_total": sum(r["tasks_total"] for r in rows),
                                "tasks_completed": sum(r["tasks_completed"] for r in rows)}
    assert report["generated_at"] in ("2024-05-01T08:00:00Z", "2024-05-01T08:00:00+00:00")


def test_every_project_and_task_is_read(clock):
    api = build_api(clock, projects=23, tasks=900)  # 3 project pages, several task pages per project
    report = run_report(api, clock)
    assert [r["project_id"] for r in report["projects"]] == sorted(p["id"] for p in api.canonical("projects"))
    assert report["totals"]["tasks_total"] == 900
    assert any(e.params.get("cursor") for e in api.requests("/v1/projects/"))


def test_bearer_token_and_credentials_are_used(clock):
    api = build_api(clock)
    run_report(api, clock)
    assert api.tokens_issued >= 1
    assert all(e.status != 401 for e in api.requests("/v1"))


def test_empty_project_has_null_rates(clock):
    api = build_api(clock, projects=12, tasks=5)  # most projects have no tasks
    rows = {r["project_id"]: r for r in run_report(api, clock)["projects"]}
    empty = [r for r in rows.values() if r["tasks_total"] == 0]
    assert empty
    assert all(r["completion_rate"] is None and r["median_minutes_to_complete"] is None for r in empty)


def test_non_2xx_raises_api_error_with_status_and_path(clock):
    from report.client import ApiError
    from shared.mock_rest import FaultConfig

    api = build_api(clock, faults=FaultConfig(scripted={"GET /v1/projects/prj_03/tasks": [404] * 10}))
    with pytest.raises(ApiError) as exc:
        run_report(api, clock)
    assert exc.value.status == 404 and "prj_03" in (exc.value.path or "")


def test_bad_credentials_raise_auth_error(clock):
    from report.client import AuthError
    from report.report import build_report

    api = build_api(clock)
    with pytest.raises(AuthError):
        build_report(make_client(api, clock, client_secret="wrong"))


def test_auth_error_is_an_api_error():
    from report.client import ApiError, AuthError

    assert issubclass(AuthError, ApiError)


@pytest.mark.change
def test_tasks_by_status(clock):
    api = build_api(clock)
    report = run_report(api, clock)
    assert report["projects"] == expected_projects(api)
    assert all(set(r["tasks_by_status"]) == {"pending", "in_progress", "completed", "rejected"}
               for r in report["projects"])
