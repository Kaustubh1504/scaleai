"""Acceptance tests for prob-006.

    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests [-m "not change"]

The API is built here from shared/ (not from the candidate's mock_services) with
a different seed than the candidate's default, and expected values come from an
independent oracle over the canonical data.
"""

import os
import statistics
import sys
from datetime import datetime
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_rest import AuthConfig, FaultConfig, MockRestAPI, scale_resources  # noqa: E402

SEED = 61
STATUSES = ("pending", "in_progress", "completed", "rejected")


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


def build_api(clock, *, seed=SEED, token_ttl_s=300.0, faults=None, rate_limit=None, on_request=None, projects=12,
              tasks=600):
    resources = {r.name: r for r in scale_resources(seed, messy=False, projects=projects, tasks=tasks,
                                                     annotators=10, submissions_per_task=(0, 0))}
    resources["projects"].default_page_size = resources["projects"].max_page_size = 10
    resources["tasks"].default_page_size, resources["tasks"].max_page_size = 10, 25
    return MockRestAPI([resources["projects"], resources["tasks"]], clock=clock,
                       faults=faults or FaultConfig(seed=seed), rate_limit=rate_limit, on_request=on_request,
                       auth=AuthConfig(client_id="hidden-id", client_secret="hidden-secret", token_ttl_s=token_ttl_s))


@pytest.fixture
def clock():
    return FakeClock(start=1_714_550_400)  # 2024-05-01T08:00:00Z


def make_client(api, clock, *, client_id="hidden-id", client_secret="hidden-secret"):
    from report.client import ApiClient

    return ApiClient(api.client(), client_id, client_secret, clock)


def run_report(api, clock):
    from report.report import build_report

    return build_report(make_client(api, clock))


# ------------------------------------------------------------------ oracle


def _minutes(task):
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return (parse(task["completed_at"]) - parse(task["created_at"])).total_seconds() / 60


def expected_projects(api):
    tasks = api.canonical("tasks")
    rows = []
    for project in sorted(api.canonical("projects"), key=lambda p: p["id"]):
        own = [t for t in tasks if t["project_id"] == project["id"]]
        done = [t for t in own if t["status"] == "completed"]
        minutes = [_minutes(t) for t in done]
        rows.append({
            "project_id": project["id"], "name": project["name"], "customer_id": project["customer"]["id"],
            "status": project["status"], "tasks_total": len(own), "tasks_completed": len(done),
            "completion_rate": round(len(done) / len(own), 4) if own else None,
            "median_minutes_to_complete": round(statistics.median(minutes), 1) if minutes else None,
            "tasks_by_status": {s: sum(t["status"] == s for t in own) for s in STATUSES},
        })
    return rows


def expected_customers(api):
    out = {}
    for project, row in zip(sorted(api.canonical("projects"), key=lambda p: p["id"]), expected_projects(api)):
        c = project["customer"]
        e = out.setdefault(c["id"], {"customer_id": c["id"], "customer_name": c["name"], "tier": c["tier"],
                                     "projects": 0, "tasks_total": 0, "tasks_completed": 0})
        e["projects"] += 1
        e["tasks_total"] += row["tasks_total"]
        e["tasks_completed"] += row["tasks_completed"]
    for e in out.values():
        e["completion_rate"] = round(e["tasks_completed"] / e["tasks_total"], 4) if e["tasks_total"] else None
    return [out[k] for k in sorted(out)]


def strip_change(rows):
    """Project rows without the mid-part-change field, so base tests pass either way."""
    return [{k: v for k, v in row.items() if k != "tasks_by_status"} for row in rows]


def expected_pages(api):
    """Number of successful GETs a crawl with per_page=10 / limit=25 needs."""
    projects = api.canonical("projects")
    tasks = api.canonical("tasks")
    pages = max(1, -(-len(projects) // 10))
    for p in projects:
        n = sum(t["project_id"] == p["id"] for t in tasks)
        pages += max(1, -(-n // 25))
    return pages
