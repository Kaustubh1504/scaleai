"""Part 3: atomic claims under concurrency, and restarts over the same storage_dir."""

import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from conftest import T0, claim, claimed_id, create, get, submit, who

THREADS = 20


def run_at_once(fn, args_list):
    """Call fn(*args) from one thread per entry, released together by a barrier."""
    barrier = threading.Barrier(len(args_list))

    def call(args):
        barrier.wait()
        return fn(*args)

    with ThreadPoolExecutor(max_workers=len(args_list)) as pool:
        return list(pool.map(call, args_list))


def test_concurrent_claims_never_share_a_task(make_client):
    client = make_client()
    create(client, *[f"t{i:02d}" for i in range(10)])
    responses = run_at_once(lambda a: claim(client, a), [(f"a{i}",) for i in range(THREADS)])
    statuses = Counter(r.status_code for r in responses)
    assert statuses == {200: 10, 204: 10}
    granted = [r.json()["id"] for r in responses if r.status_code == 200]
    assert sorted(granted) == [f"t{i:02d}" for i in range(10)]
    for i in range(10):
        assert len(get(client, f"t{i:02d}")["leases"]) == 1


def test_concurrent_claims_respect_redundancy(make_client):
    client = make_client(redundancy=3)
    create(client, *[f"t{i}" for i in range(5)])
    responses = run_at_once(lambda a: claim(client, a), [(f"a{i:02d}",) for i in range(THREADS)])
    assert Counter(r.status_code for r in responses) == {200: 15, 204: 5}
    holders = {}
    for i, resp in enumerate(responses):
        if resp.status_code == 200:
            holders.setdefault(resp.json()["id"], set()).add(f"a{i:02d}")
    assert sorted(holders) == [f"t{i}" for i in range(5)]
    assert all(len(h) == 3 for h in holders.values())
    for task_id, expected in holders.items():
        assert {lease["annotator_id"] for lease in get(client, task_id)["leases"]} == expected


def test_same_annotator_concurrent_claims_get_one_task(make_client):
    client = make_client()
    create(client, "t1", "t2", "t3")
    responses = run_at_once(lambda: claim(client, "alice"), [()] * THREADS)
    assert {r.status_code for r in responses} == {200}
    assert {r.json()["id"] for r in responses} == {"t1"}
    assert {r.json()["lease_expires_at"] for r in responses} == {T0 + 60}
    assert [len(get(client, t)["leases"]) for t in ("t1", "t2", "t3")] == [1, 0, 0]


def test_concurrent_submissions_finalize_once(make_client):
    client = make_client(redundancy=3)
    create(client, "t1")
    for a in ("alice", "bob", "carol"):
        assert claimed_id(client, a) == "t1"
    votes = [("alice", "cat"), ("bob", "dog"), ("carol", "cat")]
    responses = run_at_once(lambda a, label: submit(client, "t1", a, label), votes)
    assert [r.status_code for r in responses] == [200, 200, 200]
    task = get(client, "t1")
    assert (task["state"], task["consensus_label"], task["agreement"]) == ("completed", "cat", 0.67)
    assert sorted(s["annotator_id"] for s in task["submissions"]) == ["alice", "bob", "carol"]


def test_mixed_load_has_no_server_errors(make_client):
    client = make_client(redundancy=3)
    create(client, *[f"t{i}" for i in range(4)])

    def work(annotator):
        resp = claim(client, annotator)
        if resp.status_code != 200:
            return [resp.status_code]
        task_id = resp.json()["id"]
        return [resp.status_code,
                client.post(f"/tasks/{task_id}/extend", headers=who(annotator)).status_code,
                submit(client, task_id, annotator).status_code]

    results = run_at_once(work, [(f"a{i:02d}",) for i in range(THREADS)])
    assert sorted(results) == sorted([[200, 200, 200]] * 12 + [[204]] * 8)
    assert [get(client, f"t{i}")["state"] for i in range(4)] == ["completed"] * 4


def test_restart_keeps_leases_and_submissions(make_client, clock):
    first = make_client(redundancy=3)
    create(first, "t1", "t2")
    for a in ("alice", "bob"):
        assert claimed_id(first, a) == "t1"
    assert submit(first, "t1", "alice").status_code == 200

    second = make_client(redundancy=3)  # same storage_dir and clock
    task = get(second, "t1")
    assert task["state"] == "leased"
    assert task["leases"] == [{"annotator_id": "bob", "expires_at": T0 + 60}]
    assert [s["annotator_id"] for s in task["submissions"]] == ["alice"]
    assert claimed_id(second, "carol") == "t1"
    assert claimed_id(second, "dave") == "t2"  # t1: 1 submission + 2 live leases
    assert claim(second, "alice").json()["id"] == "t2"  # alice already submitted t1

    clock.advance(30)
    assert second.post("/tasks/t1/extend", headers=who("bob")).json()["lease_expires_at"] == T0 + 90
    assert submit(second, "t1", "bob", "dog").status_code == 200
    assert submit(second, "t1", "carol").status_code == 200
    assert get(second, "t1")["state"] == "completed"

    third = make_client(redundancy=3)
    task = get(third, "t1")
    assert (task["state"], task["consensus_label"], task["agreement"]) == ("completed", "cat", 0.67)


def test_restart_honours_lease_until_expiry(make_client, clock):
    first = make_client()
    create(first, "t1")
    claimed_id(first, "alice")
    second = make_client()
    assert claim(second, "bob").status_code == 204
    assert claim(second, "alice").json()["lease_expires_at"] == T0 + 60
    clock.advance(60)
    assert claimed_id(second, "bob") == "t1"
