"""Acceptance tests for prob-009.

    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests [-m "not change"]

The API is built here from shared/ (not from the candidate's mock_services) with
a different seed and API key than the candidate's default, and expected file
contents come from the API's own rendering of the records (what the wire shows).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_rest import AuthConfig, FaultConfig, MockRestAPI, scale_resources  # noqa: E402

SEED = 91
API_KEY = "key_hidden_91"
START = 1_714_550_400  # 2024-05-01T08:00:00Z
PROJECTS = [f"prj_{i:02d}" for i in range(1, 9)]


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


def build_api(clock, *, seed=SEED, faults=None, rate_limit=None, on_request=None, projects=8, tasks=400):
    resources = {r.name: r for r in scale_resources(seed, projects=projects, tasks=tasks, annotators=10,
                                                     submissions_per_task=(0, 0))}
    resources["tasks"].default_page_size, resources["tasks"].max_page_size = 10, 25
    if faults is not None and faults.seed == 0:
        faults.seed = seed
    return MockRestAPI([resources["projects"], resources["tasks"]], clock=clock,
                       faults=faults or FaultConfig(seed=seed), rate_limit=rate_limit, on_request=on_request,
                       auth=AuthConfig(mode="api_key", api_key=API_KEY))


@pytest.fixture
def clock():
    return FakeClock(start=START)


@pytest.fixture
def out(tmp_path):
    return tmp_path / "exports"


def make_exporter(api, clock, out_dir, *, api_key=API_KEY):
    from exporter.export import Exporter

    return Exporter(api.client(), api_key, clock, out_dir)


def run_export(api, clock, out_dir, project_ids=PROJECTS):
    return make_exporter(api, clock, out_dir).export(list(project_ids))


# ------------------------------------------------------------------ oracle


def expected_records(api, project_id):
    """The project's tasks exactly as the API serves them, in API order."""
    return [shown for clean, shown in zip(api.canonical("tasks"), api.rendered("tasks"))
            if clean["project_id"] == project_id]


def expected_pages(api, project_ids, limit=25):
    counts = [len(expected_records(api, p)) for p in project_ids]
    return sum(max(1, -(-n // limit)) for n in counts)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_manifest(out_dir):
    return json.loads((Path(out_dir) / "manifest.json").read_text())


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def assert_complete(api, out_dir, project_id, entry):
    path = Path(out_dir) / f"{project_id}.jsonl"
    want = expected_records(api, project_id)
    assert read_lines(path) == want, f"{project_id}.jsonl does not match the API's records"
    assert entry == {"status": "complete", "tasks": len(want), "file": f"{project_id}.jsonl", "sha256": sha256(path)}


def result_files(out_dir):
    """Every file name in out_dir (including hidden temp files)."""
    return sorted(p.name for p in Path(out_dir).iterdir())


def tasks_requests(api, project_id=None):
    prefix = f"/v1/projects/{project_id}/tasks" if project_id else "/v1/projects/"
    return [e for e in api.requests(prefix) if e.path.endswith("/tasks")]
