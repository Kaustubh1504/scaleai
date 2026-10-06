"""Part 2: per-tenant token buckets, Retry-After, what costs a token."""

import pytest

from conftest import created, get, is_replay, post


def burst(client, tenant, n):
    return [post(client, tenant=tenant, body={"project": f"p{i}", "payload": {}}).status_code for i in range(n)]


def retry_after(resp) -> int:
    assert resp.status_code == 429, resp.text
    assert isinstance(resp.json()["detail"], str)
    return int(resp.headers["Retry-After"])


@pytest.mark.parametrize("tenant, size", [("globex", 5), ("acme", 20), ("tinyco", 2)])
def test_bucket_starts_full(client, tenant, size):
    assert burst(client, tenant, size) == [201] * size
    assert post(client, tenant=tenant).status_code == 429
    assert len(get(client, "/tasks", tenant=tenant).json()["tasks"]) == size


def test_free_plan_retry_after_and_refill(client, clock):
    burst(client, "globex", 5)
    assert retry_after(post(client, tenant="globex")) == 1
    clock.advance(1)
    assert post(client, tenant="globex").status_code == 201
    assert post(client, tenant="globex").status_code == 429


def test_refill_is_continuous(client, clock):
    burst(client, "globex", 5)
    clock.advance(0.5)
    assert retry_after(post(client, tenant="globex")) == 1
    clock.advance(0.5)
    assert post(client, tenant="globex").status_code == 201


def test_retry_after_rounds_up(client, clock):
    burst(client, "tinyco", 2)
    assert retry_after(post(client, tenant="tinyco")) == 4
    clock.advance(1)
    assert retry_after(post(client, tenant="tinyco")) == 3
    clock.advance(1.5)  # 0.625 tokens: 1.5 s to go
    assert retry_after(post(client, tenant="tinyco")) == 2
    clock.advance(1)  # 0.875 tokens: 0.5 s to go
    assert retry_after(post(client, tenant="tinyco")) == 1
    clock.advance(0.5)
    assert post(client, tenant="tinyco").status_code == 201


def test_pro_retry_after_is_at_least_one(client):
    burst(client, "acme", 20)
    assert retry_after(post(client, tenant="acme")) == 1


def test_refill_caps_at_burst(client, clock):
    clock.advance(1000)
    assert burst(client, "globex", 6) == [201] * 5 + [429]
    clock.advance(1000)
    assert burst(client, "globex", 6) == [201] * 5 + [429]


def test_tenants_are_isolated(client):
    assert burst(client, "globex", 6)[-1] == 429
    assert burst(client, "initech", 5) == [201] * 5
    assert burst(client, "acme", 20) == [201] * 20


def test_replays_are_free_and_served_when_empty(client):
    original = created(post(client, tenant="globex", key="k"))
    for _ in range(10):
        resp = post(client, tenant="globex", key="k")
        assert resp.status_code == 201 and is_replay(resp) and resp.json() == original
    assert burst(client, "globex", 5) == [201] * 4 + [429]
    resp = post(client, tenant="globex", key="k")
    assert resp.status_code == 201 and is_replay(resp)


def test_rejected_requests_are_free(client):
    created(post(client, tenant="globex", key="k"))
    for _ in range(5):
        assert post(client, tenant="globex", raw='{"project": ""}').status_code == 422
        assert post(client, tenant="globex", key="bad key").status_code == 400
        assert post(client, tenant="globex", key="k", body={"project": "x", "payload": {}}).status_code == 409
    assert burst(client, "globex", 5) == [201] * 4 + [429]


def test_429_is_not_recorded_and_creates_nothing(client, clock):
    burst(client, "globex", 5)
    for _ in range(3):
        assert post(client, tenant="globex", key="later").status_code == 429
    assert len(get(client, "/tasks", tenant="globex").json()["tasks"]) == 5
    clock.advance(1)
    resp = post(client, tenant="globex", key="later")
    assert resp.status_code == 201 and not is_replay(resp)


def test_gets_are_not_limited(client):
    task = created(post(client, tenant="tinyco"))
    for _ in range(10):
        assert get(client, f"/tasks/{task['id']}", tenant="tinyco").status_code == 200
        assert get(client, "/tasks", tenant="tinyco").status_code == 200
    assert post(client, tenant="tinyco").status_code == 201


def remaining(resp) -> int:
    return int(resp.headers["X-RateLimit-Remaining"])


@pytest.mark.change
def test_remaining_header_counts_down(client):
    seen = [remaining(post(client, tenant="globex", body={"project": f"p{i}", "payload": {}})) for i in range(5)]
    assert seen == [4, 3, 2, 1, 0]
    assert remaining(post(client, tenant="globex")) == 0


@pytest.mark.change
def test_remaining_header_is_floor_after_refill(client, clock):
    created(post(client, tenant="tinyco", key="k"))
    created(post(client, tenant="tinyco"))
    resp = post(client, tenant="tinyco")
    assert resp.status_code == 429 and remaining(resp) == 0
    clock.advance(3)  # 0.75 tokens
    resp = post(client, tenant="tinyco", key="k")
    assert is_replay(resp) and remaining(resp) == 0
    clock.advance(5)  # 2 tokens (capped)
    replay = post(client, tenant="tinyco", key="k")
    assert is_replay(replay) and remaining(replay) == 2
    resp = post(client, tenant="tinyco")
    assert resp.status_code == 201 and remaining(resp) == 1


@pytest.mark.change
def test_remaining_header_on_pro_plan(client, clock):
    assert remaining(post(client, tenant="acme")) == 19
    burst(client, "acme", 19)
    clock.advance(0.5)  # 5 tokens
    assert remaining(post(client, tenant="acme")) == 4
