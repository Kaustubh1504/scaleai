"""API tests: the full POST /tasks pipeline, restarts and concurrency."""

import threading

import pytest
from fastapi.testclient import TestClient

from app.main import create_app, load_tenants
from mock_services.clock import FakeClock

CONFIG = {"plans": {"free": {"burst": 3, "refill_per_s": 1.0}, "pro": {"burst": 50, "refill_per_s": 10.0}},
          "tenants": {"a": {"plan": "pro"}, "b": {"plan": "free"}}}
BODY = {"project": "p", "payload": {"x": 1}}


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def build(tmp_path, clock):
    return lambda: TestClient(create_app(storage_dir=tmp_path, clock=clock, tenants=CONFIG))


def post(client, tenant="a", key=None, body=BODY):
    headers = {"X-Tenant-Id": tenant, **({"Idempotency-Key": key} if key else {})}
    return client.post("/tasks", json=body, headers=headers)


def test_default_config_loads():
    assert set(load_tenants()["tenants"]) == {"acme", "globex", "initech"}


def test_create_get_list_and_isolation(build):
    client = build()
    resp = post(client)
    assert resp.status_code == 201 and resp.headers["X-RateLimit-Remaining"] == "49"
    task = resp.json()
    assert task["created_at"] == "2023-11-14T22:13:20+00:00"
    assert client.get(f"/tasks/{task['id']}", headers={"X-Tenant-Id": "a"}).json() == task
    assert client.get(f"/tasks/{task['id']}", headers={"X-Tenant-Id": "b"}).status_code == 404
    assert client.get("/tasks", headers={"X-Tenant-Id": "b"}).json() == {"tasks": []}


def test_check_order(build):
    client = build()
    assert client.post("/tasks", content=b"{").status_code == 400
    assert client.post("/tasks", content=b"{", headers={"X-Tenant-Id": "zz", "Idempotency-Key": "a b"}).status_code == 403
    assert client.post("/tasks", content=b"{", headers={"X-Tenant-Id": "a", "Idempotency-Key": "a b"}).status_code == 400
    assert client.post("/tasks", content=b"{", headers={"X-Tenant-Id": "a"}).status_code == 422


def test_replay_conflict_and_rate_limit_interplay(build, clock):
    client = build()
    original = post(client, "b", key="k").json()
    assert [post(client, "b").status_code for _ in range(3)] == [201, 201, 429]
    replay = post(client, "b", key="k")
    assert replay.status_code == 201 and replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json() == original and replay.headers["X-RateLimit-Remaining"] == "0"
    assert post(client, "b", key="k", body={"project": "q", "payload": {}}).status_code == 409
    limited = post(client, "b", key="new")
    assert limited.status_code == 429 and limited.headers["Retry-After"] == "1"
    clock.advance(1)
    fresh = post(client, "b", key="new")
    assert fresh.status_code == 201 and "Idempotent-Replayed" not in fresh.headers


def test_restart_and_expiry(build, clock, tmp_path):
    original = post(build(), key="k").json()
    client = build()
    assert post(client, key="k").json() == original
    assert client.get("/tasks", headers={"X-Tenant-Id": "a"}).json() == {"tasks": [original]}
    assert (tmp_path / "intake.sqlite3").exists()
    clock.advance(24 * 3600)
    fresh = post(build(), key="k")
    assert fresh.status_code == 201 and fresh.json()["id"] != original["id"]


def test_concurrent_same_key_across_app_instances(build):
    """Separate apps over one storage dir act like separate processes: only the DB constraint protects them."""
    clients = [build() for _ in range(12)]
    barrier, out = threading.Barrier(len(clients)), []

    def go(c):
        barrier.wait()
        out.append(post(c, key="same"))

    threads = [threading.Thread(target=go, args=(c,)) for c in clients]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert {r.status_code for r in out} == {201}
    assert sum("Idempotent-Replayed" not in r.headers for r in out) == 1
    assert len(clients[0].get("/tasks", headers={"X-Tenant-Id": "a"}).json()["tasks"]) == 1
