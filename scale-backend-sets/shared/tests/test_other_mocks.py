import asyncio

import httpx
import pytest

from shared.fake_clock import FakeClock
from shared.mock_api import MockRecordsAPI
from shared.mock_webhook_receiver import WebhookReceiver, sign
from shared.mock_worker import (
    MockWorker,
    WorkerFleet,
    WorkerOverloadedError,
    WorkerTimeoutError,
    WorkerUnreachableError,
    worker_transport,
)

# ------------------------------------------------------------------ fake clock


def test_fake_clock_timers_fire_in_order():
    clock = FakeClock(start=100)
    fired = []
    clock.call_later(5, lambda: fired.append(("b", clock.time())))
    clock.call_later(2, lambda: fired.append(("a", clock.time())))
    handle = clock.call_later(3, lambda: fired.append(("x", clock.time())))
    handle.cancel()
    clock.advance(10)
    assert fired == [("a", 102), ("b", 105)] and clock.time() == 110
    clock.sleep(1.5)
    assert clock.sleeps == [1.5] and clock.time() == 111.5
    with pytest.raises(ValueError):
        clock.advance(-1)


# ------------------------------------------------------------------ workers


def test_worker_states():
    clock = FakeClock()
    w = MockWorker("w1", capacity=1, latency_s=0.5, clock=clock)
    assert w.process({"id": "t1"}) == {"task_id": "t1", "worker_id": "w1", "status": "done"}
    assert clock.time() == 1_700_000_000.5 and clock.sleeps == []
    w.slow(10)
    with pytest.raises(WorkerTimeoutError):
        w.process({"id": "t2"}, timeout=1.0)
    w.go_silent()
    assert w.heartbeat() is None
    with pytest.raises(WorkerTimeoutError):
        w.process({"id": "t3"}, timeout=2.0)
    w.kill()
    with pytest.raises(WorkerUnreachableError):
        w.process({"id": "t4"})
    w.revive()
    w.crash_on_next()
    with pytest.raises(WorkerUnreachableError):
        w.process({"id": "t5"})
    assert not w.alive and w.in_flight == 0
    assert [t["id"] for t in w.completed] == ["t1"]


def test_worker_capacity():
    w = MockWorker("w1", capacity=1)
    w.in_flight = 1
    with pytest.raises(WorkerOverloadedError):
        w.process("t")


def test_worker_die_after():
    w = MockWorker("w1")
    w.die_after(2)
    w.process("a")
    w.process("b")
    with pytest.raises(WorkerUnreachableError):
        w.process("c")


def test_fleet_heartbeats():
    clock = FakeClock(start=0)
    fleet = WorkerFleet([MockWorker("a", clock=clock), MockWorker("b", clock=clock)], clock=clock, interval_s=1)
    seen = []
    fleet.run(3, seen.append)
    assert len(seen) == 6
    fleet["b"].kill()
    fleet.run(2, seen.append)
    assert [hb["worker_id"] for hb in seen[6:]] == ["a", "a"] and seen[-1]["ts"] == 5


def test_worker_transport():
    w1, w2 = MockWorker("w1"), MockWorker("w2")
    client = httpx.Client(transport=worker_transport({"http://w1": w1, "http://w2": w2}))
    assert client.post("http://w1/process", json={"task": {"id": 1}}).json()["result"]["worker_id"] == "w1"
    assert client.get("http://w2/health").json()["state"] == "healthy"
    w2.kill()
    with pytest.raises(httpx.ConnectError):
        client.post("http://w2/process", json={"task": {"id": 2}})
    w1.go_silent()
    with pytest.raises(httpx.ReadTimeout):
        client.get("http://w1/health")


# ------------------------------------------------------------------ webhooks


def test_webhook_receiver_scripts_and_signatures():
    clock = FakeClock(start=1000)
    r = WebhookReceiver(secret="s3cret", clock=clock)
    r.script_event("evt_1", [500, "timeout", "429:7"])
    client = httpx.Client(transport=r.transport())
    body = b'{"id": "evt_1"}'
    headers = {"X-Webhook-Signature": sign("s3cret", body, 1000), "content-type": "application/json"}
    assert client.post("http://hook/x", content=body, headers=headers).status_code == 500
    with pytest.raises(httpx.ReadTimeout):
        client.post("http://hook/x", content=body, headers=headers)
    resp = client.post("http://hook/x", content=body, headers=headers)
    assert resp.status_code == 429 and resp.headers["Retry-After"] == "7"
    assert client.post("http://hook/x", content=body, headers=headers).status_code == 200
    assert r.accepted_event_ids() == ["evt_1"]
    assert len(r.attempts_for("evt_1")) == 4
    assert all(d.signature_valid for d in r.deliveries)
    client.post("http://hook/x", content=b'{"id": "evt_2"}', headers={"X-Webhook-Signature": "t=1000,v1=bad"})
    assert r.deliveries[-1].signature_valid is False


def test_webhook_global_script_and_drop():
    r = WebhookReceiver()
    r.script(["drop", 503])
    client = httpx.Client(transport=r.transport())
    with pytest.raises(httpx.ConnectError):
        client.post("http://hook/", json={"id": "a"})
    assert client.post("http://hook/", json={"id": "a"}).status_code == 503
    assert client.post("http://hook/", json={"id": "a"}).status_code == 200
    assert len(r.deliveries) == 2  # dropped requests never arrive


# ------------------------------------------------------------------ third-party API


def api_client(api):
    return httpx.Client(transport=api.transport(), base_url="http://api")


def token(client):
    return client.post("/oauth/token", json={"client_id": "client", "client_secret": "secret"}).json()["access_token"]


def test_api_pagination_auth_and_expiry():
    clock = FakeClock()
    api = MockRecordsAPI([{"id": f"r{i:02d}"} for i in range(25)], clock=clock, token_ttl_s=10)
    c = api_client(api)
    assert c.get("/v1/records").status_code == 401
    auth = {"Authorization": f"Bearer {token(c)}"}
    ids, cursor = [], None
    while True:
        params = {"limit": 10, **({"cursor": cursor} if cursor else {})}
        page = c.get("/v1/records", params=params, headers=auth).json()
        ids += [r["id"] for r in page["data"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert ids == [f"r{i:02d}" for i in range(25)]
    clock.advance(10)
    assert c.get("/v1/records", headers=auth).json() == {"error": "token_expired"}
    assert c.get("/v1/records", params={"cursor": "garbage"}, headers={"Authorization": f"Bearer {token(c)}"}
                 ).status_code == 400


def test_api_scripted_pages_and_rate_limit():
    clock = FakeClock()
    api = MockRecordsAPI([{"id": i} for i in range(30)], clock=clock, rpm_limit=3, window_s=60)
    api.script_page(10, [503, "429:4"])
    c = api_client(api)
    auth = {"Authorization": f"Bearer {token(c)}"}
    first = c.get("/v1/records", params={"limit": 10}, headers=auth).json()
    cursor = first["next_cursor"]
    assert c.get("/v1/records", params={"limit": 10, "cursor": cursor}, headers=auth).status_code == 503
    r = c.get("/v1/records", params={"limit": 10, "cursor": cursor}, headers=auth)
    assert r.status_code == 429 and r.headers["Retry-After"] == "4"
    r = c.get("/v1/records", params={"limit": 10, "cursor": cursor}, headers=auth)
    assert r.status_code == 429 and r.headers["Retry-After"] == "60"  # window exhausted
    clock.advance(60)
    assert c.get("/v1/records", params={"limit": 10, "cursor": cursor}, headers=auth).status_code == 200


def test_api_async_transport():
    api = MockRecordsAPI([{"id": 1}])

    async def main():
        async with httpx.AsyncClient(transport=api.transport(), base_url="http://api") as c:
            tok = (await c.post("/oauth/token", json={"client_id": "client", "client_secret": "secret"})).json()
            return (await c.get("/v1/records/1", headers={"Authorization": f"Bearer {tok['access_token']}"})).json()

    assert asyncio.run(main()) == {"id": 1}


def test_poison_predicate_crashes_worker():
    from shared.mock_worker import WorkerCrashedError

    w = MockWorker("w1", crash_if=lambda task: task == "poison")
    assert w.process("ok")["status"] == "done"
    with pytest.raises(WorkerCrashedError):
        w.process("poison")
    with pytest.raises(WorkerUnreachableError) as exc:
        w.process("ok")
    assert not isinstance(exc.value, WorkerCrashedError)  # already dead: refused, not crashed
