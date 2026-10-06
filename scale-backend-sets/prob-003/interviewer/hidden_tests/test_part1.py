"""Part 1: task creation, validation, idempotent replays, tenant scoping."""

import pytest

from conftest import BODY, created, get, is_replay, parse_ts, post

LONG_KEY = "k" * 64


def test_create_returns_task(client, clock):
    task = created(post(client))
    assert set(task) == {"id", "tenant_id", "project", "payload", "priority", "created_at"}
    assert isinstance(task["id"], str) and task["id"]
    assert (task["tenant_id"], task["project"], task["payload"], task["priority"]) == (
        "acme", "lidar-3d", {"scene": "s-001", "frames": 120}, 7)
    assert parse_ts(task["created_at"]) == pytest.approx(clock.time(), abs=1e-3)


def test_default_priority_and_created_at_follows_clock(client, clock):
    clock.advance(3600)
    task = created(post(client, body={"project": "p", "payload": {}}))
    assert task["priority"] == 5
    assert parse_ts(task["created_at"]) == pytest.approx(clock.time(), abs=1e-3)


def test_ids_are_unique(client):
    ids = {created(post(client))["id"] for _ in range(5)}
    assert len(ids) == 5


@pytest.mark.parametrize("tenant, status", [(None, 400), ("", 400), ("umbrella", 403)])
def test_tenant_header(client, tenant, status):
    assert post(client, tenant=tenant).status_code == status
    assert get(client, "/tasks", tenant=tenant).status_code == status
    assert get(client, "/tasks/whatever", tenant=tenant).status_code == status


@pytest.mark.parametrize("key", ["", "has space", "k" * 65, "key!", "a/b", "a.b"])
def test_bad_idempotency_key_is_400(client, key):
    assert post(client, key=key).status_code == 400


@pytest.mark.parametrize("key", ["a", LONG_KEY, "Order_2024-01", "0-_-0"])
def test_good_idempotency_keys(client, key):
    assert post(client, key=key).status_code == 201


@pytest.mark.parametrize("raw", [
    "", "{", "[]", "null", '"text"',
    '{"payload": {}}',
    '{"project": "", "payload": {}}',
    '{"project": 7, "payload": {}}',
    '{"project": "p"}',
    '{"project": "p", "payload": [1, 2]}',
    '{"project": "p", "payload": "x"}',
    '{"project": "p", "payload": {}, "priority": 10}',
    '{"project": "p", "payload": {}, "priority": -1}',
    '{"project": "p", "payload": {}, "priority": "3"}',
    '{"project": "p", "payload": {}, "priority": 3.0}',
    '{"project": "p", "payload": {}, "priority": true}',
    '{"project": "p", "payload": {}, "owner": "bob"}',
])
def test_invalid_body_is_422(client, raw):
    assert post(client, raw=raw).status_code == 422
    assert get(client, "/tasks").json()["tasks"] == []


@pytest.mark.parametrize("priority", [0, 9])
def test_priority_bounds_inclusive(client, priority):
    assert created(post(client, body={**BODY, "priority": priority}))["priority"] == priority


def test_order_of_checks(client):
    assert post(client, tenant=None, raw="{").status_code == 400
    assert post(client, tenant="umbrella", key="bad key", raw="{").status_code == 403
    assert post(client, key="bad key", raw="{").status_code == 400
    created(post(client, key="k1"))
    assert post(client, key="k1", raw='{"project": ""}').status_code == 422


def test_replay_returns_original(client):
    first = post(client, key="order-1")
    original = created(first)
    assert not is_replay(first)
    again = post(client, key="order-1")
    assert again.status_code == 201
    assert again.json() == original
    assert is_replay(again)
    assert get(client, "/tasks").json()["tasks"] == [original]


def test_same_body_ignores_key_order_whitespace_and_default(client):
    original = created(post(client, key="k", raw='{"project": "p", "payload": {"b": {"y": 1, "x": 2}, "a": 1}}'))
    again = post(client, key="k", raw='{ "priority" : 5,\n "payload":{"a":1,"b":{"x":2,"y":1}}, "project":"p" }')
    assert again.status_code == 201 and is_replay(again)
    assert again.json() == original


@pytest.mark.parametrize("other", [
    {**BODY, "priority": 1},
    {**BODY, "project": "other"},
    {**BODY, "payload": {"scene": "s-002", "frames": 120}},
])
def test_same_key_different_body_is_409(client, other):
    original = created(post(client, key="k"))
    assert post(client, key="k", body=other).status_code == 409
    assert get(client, "/tasks").json()["tasks"] == [original]
    assert is_replay(post(client, key="k"))


def test_keys_are_scoped_per_tenant(client):
    a = created(post(client, tenant="acme", key="shared"))
    resp = post(client, tenant="globex", key="shared", body={"project": "q", "payload": {}})
    g = created(resp)
    assert not is_replay(resp)
    assert a["id"] != g["id"] and g["tenant_id"] == "globex"
    assert is_replay(post(client, tenant="acme", key="shared"))


def test_failed_request_is_not_recorded(client):
    assert post(client, key="k", raw='{"project": ""}').status_code == 422
    resp = post(client, key="k")
    assert resp.status_code == 201 and not is_replay(resp)


def test_no_key_never_deduplicates(client):
    created(post(client))
    created(post(client))
    assert len(get(client, "/tasks").json()["tasks"]) == 2


def test_get_task_owner_only(client):
    task = created(post(client, tenant="acme"))
    resp = get(client, f"/tasks/{task['id']}", tenant="acme")
    assert resp.status_code == 200 and resp.json() == task
    assert get(client, f"/tasks/{task['id']}", tenant="globex").status_code == 404
    assert get(client, "/tasks/does-not-exist", tenant="acme").status_code == 404


def test_list_in_creation_order_per_tenant(client, clock):
    mine = []
    for i in range(4):
        mine.append(created(post(client, tenant="acme", body={"project": f"p{i}", "payload": {"i": i}})))
        created(post(client, tenant="globex", body={"project": f"g{i}", "payload": {}}))
    resp = get(client, "/tasks", tenant="acme")
    assert resp.status_code == 200
    assert resp.json() == {"tasks": mine}
    assert [t["project"] for t in get(client, "/tasks", tenant="globex").json()["tasks"]] == [f"g{i}" for i in range(4)]
    assert get(client, "/tasks", tenant="initech").json() == {"tasks": []}
