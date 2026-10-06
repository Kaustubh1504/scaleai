"""Part 3: durability across restarts, concurrent identical requests, record expiry."""

import threading

from fastapi.testclient import TestClient

from conftest import BODY, created, get, is_replay, post

DAY = 86400


def restart(make_app, **kwargs) -> TestClient:
    return TestClient(make_app(**kwargs))


def test_tasks_survive_restart(make_app):
    before = TestClient(make_app())
    acme = [created(post(before, body={"project": f"p{i}", "payload": {"i": i}})) for i in range(3)]
    globex = created(post(before, tenant="globex"))

    after = restart(make_app)
    assert get(after, "/tasks").json() == {"tasks": acme}
    assert get(after, "/tasks", tenant="globex").json() == {"tasks": [globex]}
    for task in acme:
        resp = get(after, f"/tasks/{task['id']}")
        assert resp.status_code == 200 and resp.json() == task
    assert get(after, f"/tasks/{globex['id']}").status_code == 404


def test_new_tasks_after_restart_keep_order(make_app):
    first = created(post(TestClient(make_app()), body={"project": "a", "payload": {}}))
    after = restart(make_app)
    second = created(post(after, body={"project": "b", "payload": {}}))
    assert get(restart(make_app), "/tasks").json() == {"tasks": [first, second]}


def test_replay_and_conflict_survive_restart(make_app):
    original = created(post(TestClient(make_app()), key="order-1"))
    after = restart(make_app)
    resp = post(after, key="order-1")
    assert resp.status_code == 201 and is_replay(resp) and resp.json() == original
    assert post(after, key="order-1", body={**BODY, "priority": 0}).status_code == 409
    assert get(after, "/tasks").json() == {"tasks": [original]}


def test_other_storage_dir_is_separate(make_app, tmp_path):
    task = created(post(TestClient(make_app()), key="k"))
    other = restart(make_app, storage_dir=tmp_path / "elsewhere")
    assert get(other, f"/tasks/{task['id']}").status_code == 404
    assert get(other, "/tasks").json() == {"tasks": []}
    resp = post(other, key="k")
    assert resp.status_code == 201 and not is_replay(resp)


def run_concurrently(app, n, request):
    """Run ``request(client)`` from n threads at once, one TestClient per thread over the same app."""
    clients = [TestClient(app) for _ in range(n)]
    barrier = threading.Barrier(n)
    results, errors = [None] * n, []

    def worker(i):
        try:
            barrier.wait(timeout=10)
            results[i] = request(clients[i], i)
        except Exception as exc:  # surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors, errors
    return results


def test_concurrent_identical_requests_create_one_task(make_app):
    app = make_app()
    responses = run_concurrently(app, 10, lambda c, i: post(c, key="same-key"))
    assert all(r.status_code in (201, 409) for r in responses), [r.status_code for r in responses]
    tasks = get(TestClient(app), "/tasks").json()["tasks"]
    assert len(tasks) == 1
    ok = [r for r in responses if r.status_code == 201]
    assert ok and all(r.json() == tasks[0] for r in ok)
    assert sum(not is_replay(r) for r in ok) == 1
    for r in responses:
        if r.status_code == 409:
            assert isinstance(r.json()["detail"], str)
    resp = post(TestClient(app), key="same-key")
    assert resp.status_code == 201 and is_replay(resp) and resp.json() == tasks[0]


def test_concurrent_distinct_keys(make_app):
    app = make_app()
    responses = run_concurrently(app, 10, lambda c, i: post(c, key=f"key-{i}", body={"project": f"p{i}", "payload": {}}))
    assert [r.status_code for r in responses] == [201] * 10
    assert len({r.json()["id"] for r in responses}) == 10
    assert len(get(TestClient(app), "/tasks").json()["tasks"]) == 10


def test_rate_limit_holds_under_concurrency(make_app):
    app = make_app()
    responses = run_concurrently(app, 10, lambda c, i: post(c, tenant="globex", key=f"k{i}"))
    codes = sorted(r.status_code for r in responses)
    assert codes == [201] * 5 + [429] * 5
    assert len(get(TestClient(app), "/tasks", tenant="globex").json()["tasks"]) == 5


def test_record_expires_after_24h(client, clock):
    original = created(post(client, key="k"))
    clock.advance(DAY - 1)
    resp = post(client, key="k")
    assert resp.status_code == 201 and is_replay(resp) and resp.json() == original
    assert post(client, key="k", body={**BODY, "priority": 0}).status_code == 409

    clock.advance(1)
    fresh = post(client, key="k")
    assert fresh.status_code == 201 and not is_replay(fresh)
    assert fresh.json()["id"] != original["id"]
    again = post(client, key="k")
    assert is_replay(again) and again.json() == fresh.json()
    assert get(client, f"/tasks/{original['id']}").status_code == 200
    assert [t["id"] for t in get(client, "/tasks").json()["tasks"]] == [original["id"], fresh.json()["id"]]


def test_expired_key_accepts_a_different_body(client, clock):
    original = created(post(client, key="k"))
    clock.advance(DAY)
    resp = post(client, key="k", body={"project": "new", "payload": {}})
    assert resp.status_code == 201 and not is_replay(resp)
    assert resp.json()["id"] != original["id"] and resp.json()["project"] == "new"
    assert post(client, key="k").status_code == 409


def test_expiry_is_measured_from_creation_not_last_replay(client, clock):
    original = created(post(client, key="k"))
    for _ in range(4):
        clock.advance(DAY / 4 - 1)
        assert post(client, key="k").json() == original
    clock.advance(4)
    resp = post(client, key="k")
    assert resp.status_code == 201 and not is_replay(resp)


def test_expiry_survives_restart(make_app, clock):
    original = created(post(TestClient(make_app()), key="k"))
    clock.advance(DAY - 1)
    after = restart(make_app)
    assert is_replay(post(after, key="k"))
    clock.advance(1)
    resp = post(restart(make_app), key="k")
    assert resp.status_code == 201 and not is_replay(resp) and resp.json()["id"] != original["id"]
