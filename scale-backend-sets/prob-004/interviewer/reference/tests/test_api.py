import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock

SEED = Path(__file__).resolve().parent.parent / "data" / "tasks_seed.json"
T0 = 1_700_000_000.0


def h(annotator):
    return {"X-Annotator-Id": annotator}


@pytest.fixture
def clock():
    return FakeClock(start=T0)


@pytest.fixture
def make_client(tmp_path, clock):
    def build(**kwargs):
        return TestClient(create_app(storage_dir=tmp_path, clock=clock, **kwargs))

    return build


def create(client, *ids, **extra):
    resp = client.post("/tasks", json={"tasks": [{"id": i, "data": {}, "labels": ["a", "b", "c"], **extra}
                                                 for i in ids]})
    assert resp.json()["created"] == list(ids)


def claim(client, annotator):
    return client.post("/tasks/claim", headers=h(annotator))


def submit(client, task_id, annotator, label="a"):
    return client.post(f"/tasks/{task_id}/submit", json={"label": label}, headers=h(annotator))


def test_seed_batch(make_client):
    body = make_client().post("/tasks", json=json.loads(SEED.read_text())).json()
    assert len(body["created"]) == 8
    assert [e["index"] for e in body["errors"]] == [8, 9, 10, 11, 12, 13, 14]


def test_invalid_config_rejected(tmp_path):
    with pytest.raises(ValueError):
        create_app(tmp_path, redundancy=0)
    with pytest.raises(ValueError):
        create_app(tmp_path, lease_seconds=0)


def test_lease_lifecycle(make_client, clock):
    client = make_client()
    create(client, "t1", "t2")
    first = claim(client, "alice").json()
    assert (first["id"], first["state"], first["lease_expires_at"]) == ("t1", "leased", T0 + 60)
    assert claim(client, "bob").json()["id"] == "t2"
    assert claim(client, "carol").status_code == 204
    clock.advance(40)
    assert claim(client, "alice").json()["lease_expires_at"] == T0 + 60  # re-claim does not extend
    assert client.post("/tasks/t1/extend", headers=h("alice")).json()["lease_expires_at"] == T0 + 100
    clock.advance(30)  # bob's lease on t2 expired at T0 + 60
    assert client.get("/tasks/t2").json()["state"] == "pending"
    assert claim(client, "carol").json()["id"] == "t2"
    assert submit(client, "t2", "bob").status_code == 409
    assert submit(client, "t1", "alice", "z").status_code == 422
    done = submit(client, "t1", "alice", "b").json()
    assert (done["state"], done["leases"], done["submissions"][0]["submitted_at"]) == ("submitted", [], T0 + 70)


def test_error_codes(make_client):
    client = make_client()
    create(client, "t1")
    assert client.post("/tasks/claim").status_code == 400
    assert client.post("/tasks/t1/submit", json={"label": "a"}, headers=h(" ")).status_code == 400
    assert client.post("/tasks/zz/extend", headers=h("alice")).status_code == 404
    assert submit(client, "zz", "alice").status_code == 404
    resp = submit(client, "t1", "alice")
    assert resp.status_code == 409 and "live lease" in resp.json()["detail"]
    assert client.post("/tasks/t1/submit", json={}, headers=h("alice")).status_code == 422


def test_consensus_with_redundancy(make_client, clock):
    client = make_client(redundancy=3)
    create(client, "t1", "t2")
    assert [claim(client, a).json()["id"] for a in ("x", "y", "z", "w")] == ["t1", "t1", "t1", "t2"]
    for a, label in (("x", "a"), ("y", "b")):
        assert submit(client, "t1", a, label).status_code == 200
    assert claim(client, "x").json()["id"] == "t2"  # x submitted t1, never gets it again
    clock.advance(60)  # z's lease on t1 expires
    assert claim(client, "v").json()["id"] == "t1"
    task = submit(client, "t1", "v", "c").json()
    assert (task["state"], task["consensus_label"], task["agreement"]) == ("disputed", None, 0.33)
    assert submit(client, "t1", "z").status_code == 409


def test_gold_stats(make_client):
    client = make_client()
    create(client, "g1", "g2", gold_label="a")
    create(client, "n1")
    for task_id, label in (("g1", "a"), ("g2", "b"), ("n1", "a")):
        claimed = claim(client, "alice").json()
        assert claimed["id"] == task_id and "gold_label" not in claimed
        submit(client, task_id, "alice", label)
    assert client.get("/annotators/alice/stats").json() == {
        "annotator_id": "alice", "gold_seen": 2, "gold_correct": 1, "accuracy": 0.5}
    assert client.get("/annotators/bob/stats").json()["accuracy"] is None


def test_restart_continues(make_client, clock):
    first = make_client(redundancy=2)
    create(first, "t1")
    claim(first, "alice")
    claim(first, "bob")
    submit(first, "t1", "alice")
    second = make_client(redundancy=2)
    assert claim(second, "carol").status_code == 204
    assert submit(second, "t1", "bob").json()["state"] == "completed"


def test_parallel_claims_are_atomic(make_client):
    client = make_client(redundancy=2)
    create(client, *[f"t{i}" for i in range(5)])
    barrier = threading.Barrier(16)

    def go(i):
        barrier.wait()
        return claim(client, f"a{i}")

    with ThreadPoolExecutor(16) as pool:
        responses = list(pool.map(go, range(16)))
    assert Counter(r.status_code for r in responses) == {200: 10, 204: 6}
    assert Counter(r.json()["id"] for r in responses if r.status_code == 200) == {f"t{i}": 2 for i in range(5)}
