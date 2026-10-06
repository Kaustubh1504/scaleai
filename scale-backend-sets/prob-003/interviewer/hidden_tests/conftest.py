"""Acceptance tests for prob-003.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from fastapi.testclient import TestClient  # noqa: E402

from mock_services.clock import FakeClock  # noqa: E402

# The config is defined here so candidate edits to data/tenants.json cannot change the outcome.
CONFIG = {
    "plans": {
        "free": {"burst": 5, "refill_per_s": 1.0},
        "pro": {"burst": 20, "refill_per_s": 10.0},
        "tiny": {"burst": 2, "refill_per_s": 0.25},
    },
    "tenants": {
        "acme": {"plan": "pro"},
        "globex": {"plan": "free"},
        "initech": {"plan": "free"},
        "tinyco": {"plan": "tiny"},
    },
}
BODY = {"project": "lidar-3d", "payload": {"scene": "s-001", "frames": 120}, "priority": 7}


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def make_app(tmp_path, clock):
    from app.main import create_app

    def build(storage_dir=None, tenants=None):
        return create_app(storage_dir=storage_dir or tmp_path, clock=clock, tenants=tenants or CONFIG)

    return build


@pytest.fixture
def client(make_app):
    return TestClient(make_app())


def post(client, tenant="acme", body=None, key=None, raw=None):
    """POST /tasks. ``raw`` sends a literal body string; ``tenant=None`` omits the header."""
    headers = {"Content-Type": "application/json"}
    if tenant is not None:
        headers["X-Tenant-Id"] = tenant
    if key is not None:
        headers["Idempotency-Key"] = key
    if raw is not None:
        return client.post("/tasks", content=raw.encode(), headers=headers)
    return client.post("/tasks", json=BODY if body is None else body, headers=headers)


def get(client, path, tenant="acme"):
    return client.get(path, headers={} if tenant is None else {"X-Tenant-Id": tenant})


def created(resp) -> dict:
    assert resp.status_code == 201, resp.text
    return resp.json()


def is_replay(resp) -> bool:
    return resp.headers.get("Idempotent-Replayed", "").lower() == "true"


def parse_ts(value: str) -> float:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert dt.utcoffset() is not None and dt.utcoffset().total_seconds() == 0
    return dt.timestamp()
