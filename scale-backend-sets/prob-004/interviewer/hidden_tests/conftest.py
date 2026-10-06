"""Acceptance tests for prob-004.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change (gold tasks) if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.
"""

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from fastapi.testclient import TestClient  # noqa: E402

from shared.fake_clock import FakeClock  # noqa: E402

T0 = 1_700_000_000.0
LABELS = ["cat", "dog", "bird"]


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


@pytest.fixture
def clock():
    return FakeClock(start=T0)


@pytest.fixture
def make_client(tmp_path, clock):
    from app.main import create_app

    def build(**kwargs) -> TestClient:
        return TestClient(create_app(storage_dir=tmp_path, clock=clock, **kwargs))

    return build


def who(annotator: str) -> dict:
    return {"X-Annotator-Id": annotator}


def create(client: TestClient, *ids: str, labels=LABELS, **extra) -> None:
    resp = client.post("/tasks", json={"tasks": [{"id": i, "data": {"n": i}, "labels": labels, **extra} for i in ids]})
    assert resp.status_code == 201, resp.text
    assert resp.json()["created"] == list(ids)


def claim(client: TestClient, annotator: str):
    return client.post("/tasks/claim", headers=who(annotator))


def claimed_id(client: TestClient, annotator: str) -> str:
    resp = claim(client, annotator)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def submit(client: TestClient, task_id: str, annotator: str, label: str = "cat"):
    return client.post(f"/tasks/{task_id}/submit", json={"label": label}, headers=who(annotator))


def get(client: TestClient, task_id: str) -> dict:
    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def ids_in_state(client: TestClient, state: str) -> list[str]:
    return [t["id"] for t in client.get("/tasks", params={"state": state}).json()["tasks"]]
