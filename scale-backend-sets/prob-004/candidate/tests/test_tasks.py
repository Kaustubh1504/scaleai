"""Tests for the existing endpoints. Add your own next to these."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock

SEED = Path(__file__).resolve().parent.parent / "data" / "tasks_seed.json"
ALICE = {"X-Annotator-Id": "alice"}


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(storage_dir=tmp_path, clock=FakeClock()))


def create(client, *tasks):
    resp = client.post("/tasks", json={"tasks": list(tasks)})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_seed_file_reports_bad_entries(client):
    body = client.post("/tasks", json=json.loads(SEED.read_text())).json()
    assert len(body["created"]) == 8
    assert [e["index"] for e in body["errors"]] == [8, 9, 10, 11, 12, 13, 14]


def test_create_and_get(client):
    body = create(client, {"id": "t1", "data": {"text": "hi"}, "labels": ["a", "b"]})
    assert body == {"created": ["t1"], "errors": []}
    task = client.get("/tasks/t1").json()
    assert task["data"] == {"text": "hi"}
    assert task["labels"] == ["a", "b"]
    assert task["state"] == "pending"
    assert task["submissions"] == []
    assert client.get("/tasks/nope").status_code == 404


def test_list_filters_by_state(client):
    create(client, {"id": "t1", "data": {}, "labels": ["a"]}, {"id": "t2", "data": {}, "labels": ["a"]})
    client.post("/tasks/t1/submit", json={"label": "a"}, headers=ALICE)
    assert [t["id"] for t in client.get("/tasks").json()["tasks"]] == ["t1", "t2"]
    assert [t["id"] for t in client.get("/tasks", params={"state": "pending"}).json()["tasks"]] == ["t2"]


def test_claim_returns_oldest_pending(client):
    assert client.post("/tasks/claim", headers=ALICE).status_code == 204
    create(client, {"id": "t1", "data": {}, "labels": ["a"]}, {"id": "t2", "data": {}, "labels": ["a"]})
    assert client.post("/tasks/claim", headers=ALICE).json()["id"] == "t1"


def test_submit(client):
    create(client, {"id": "t1", "data": {}, "labels": ["a", "b"]})
    assert client.post("/tasks/t1/submit", json={"label": "c"}, headers=ALICE).status_code == 422
    resp = client.post("/tasks/t1/submit", json={"label": "b"}, headers=ALICE)
    assert resp.status_code == 200
    assert resp.json()["state"] == "submitted"
    assert [(s["annotator_id"], s["label"]) for s in resp.json()["submissions"]] == [("alice", "b")]
    assert client.post("/tasks/t1/submit", json={"label": "a"}, headers=ALICE).status_code == 409
