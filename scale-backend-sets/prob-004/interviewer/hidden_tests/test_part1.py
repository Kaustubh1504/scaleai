"""Part 1: leases and the pending -> leased -> submitted state machine (redundancy 1)."""

import pytest

from conftest import T0, claim, claimed_id, create, get, ids_in_state, submit, who


def test_claim_leases_oldest_task(make_client):
    client = make_client()
    create(client, "t1", "t2")
    create(client, "t3")
    resp = claim(client, "alice")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "t1"
    assert body["lease_expires_at"] == T0 + 60
    assert body["state"] == "leased"
    assert body["leases"] == [{"annotator_id": "alice", "expires_at": T0 + 60}]
    task = get(client, "t1")
    assert task["state"] == "leased"
    assert task["leases"] == [{"annotator_id": "alice", "expires_at": T0 + 60}]
    assert get(client, "t2")["state"] == "pending"


def test_timestamps_come_from_the_injected_clock(make_client, clock):
    client = make_client()
    create(client, "t1")
    assert get(client, "t1")["created_at"] == T0
    clock.advance(5)
    claimed_id(client, "alice")
    clock.advance(7)
    assert submit(client, "t1", "alice").status_code == 200
    assert get(client, "t1")["submissions"][0]["submitted_at"] == T0 + 12


def test_leased_tasks_go_to_different_annotators(make_client):
    client = make_client()
    create(client, "t1", "t2", "t3")
    assert [claimed_id(client, a) for a in ("alice", "bob", "carol")] == ["t1", "t2", "t3"]
    resp = claim(client, "dave")
    assert resp.status_code == 204
    assert resp.content == b""


def test_no_tasks_is_204(make_client):
    assert claim(make_client(), "alice").status_code == 204


def test_claim_again_returns_same_lease_unchanged(make_client, clock):
    client = make_client()
    create(client, "t1", "t2")
    first = claim(client, "alice").json()
    clock.advance(10)
    again = claim(client, "alice").json()
    assert again["id"] == "t1"
    assert again["lease_expires_at"] == first["lease_expires_at"] == T0 + 60
    assert get(client, "t2")["state"] == "pending"


def test_expired_lease_makes_task_claimable(make_client, clock):
    client = make_client()
    create(client, "t1")
    claimed_id(client, "alice")
    clock.advance(59.9)
    assert claim(client, "bob").status_code == 204
    clock.advance(0.1)  # exactly at expires_at: expired
    resp = claim(client, "bob")
    assert resp.status_code == 200
    assert resp.json()["id"] == "t1"
    assert resp.json()["lease_expires_at"] == T0 + 120
    assert get(client, "t1")["leases"] == [{"annotator_id": "bob", "expires_at": T0 + 120}]


def test_expiry_visible_without_a_claim(make_client, clock):
    client = make_client()
    create(client, "t1", "t2")
    claimed_id(client, "alice")
    assert ids_in_state(client, "leased") == ["t1"]
    clock.advance(60)
    task = get(client, "t1")
    assert task["state"] == "pending"
    assert task["leases"] == []
    assert ids_in_state(client, "pending") == ["t1", "t2"]
    assert ids_in_state(client, "leased") == []


def test_custom_lease_seconds(make_client, clock):
    client = make_client(lease_seconds=5)
    create(client, "t1")
    assert claim(client, "alice").json()["lease_expires_at"] == T0 + 5
    clock.advance(5)
    assert claimed_id(client, "bob") == "t1"


def test_extend_by_holder(make_client, clock):
    client = make_client()
    create(client, "t1")
    claimed_id(client, "alice")
    clock.advance(30)
    resp = client.post("/tasks/t1/extend", headers=who("alice"))
    assert resp.status_code == 200
    assert resp.json()["lease_expires_at"] == T0 + 90
    assert get(client, "t1")["leases"] == [{"annotator_id": "alice", "expires_at": T0 + 90}]
    clock.advance(50)  # T0 + 80: the original lease would have expired
    assert claim(client, "bob").status_code == 204
    clock.advance(10)
    assert claimed_id(client, "bob") == "t1"


def test_extend_conflicts(make_client, clock):
    client = make_client()
    create(client, "t1", "t2")
    claimed_id(client, "alice")
    assert client.post("/tasks/t1/extend", headers=who("bob")).status_code == 409
    assert client.post("/tasks/t2/extend", headers=who("alice")).status_code == 409
    clock.advance(60)
    resp = client.post("/tasks/t1/extend", headers=who("alice"))
    assert resp.status_code == 409
    assert resp.json()["detail"]
    assert client.post("/tasks/nope/extend", headers=who("alice")).status_code == 404


def test_submit_by_holder(make_client, clock):
    client = make_client()
    create(client, "t1")
    claimed_id(client, "alice")
    clock.advance(3)
    resp = submit(client, "t1", "alice", "dog")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "submitted"
    assert body["leases"] == []
    assert body["submissions"] == [{"annotator_id": "alice", "label": "dog", "submitted_at": T0 + 3}]
    assert get(client, "t1")["state"] == "submitted"
    assert ids_in_state(client, "submitted") == ["t1"]
    assert claim(client, "bob").status_code == 204
    assert claim(client, "alice").status_code == 204


def test_submit_without_live_lease_is_409(make_client, clock):
    client = make_client()
    create(client, "t1", "t2")
    assert submit(client, "t1", "alice").status_code == 409  # never claimed
    claimed_id(client, "alice")
    resp = submit(client, "t1", "bob")  # someone else's lease
    assert resp.status_code == 409
    assert resp.json()["detail"]
    clock.advance(60)
    assert submit(client, "t1", "alice").status_code == 409  # own lease expired
    assert get(client, "t1")["submissions"] == []


def test_submit_after_expiry_and_reclaim_by_other(make_client, clock):
    client = make_client()
    create(client, "t1")
    claimed_id(client, "alice")
    clock.advance(61)
    claimed_id(client, "bob")
    assert submit(client, "t1", "alice").status_code == 409
    assert submit(client, "t1", "bob").status_code == 200


def test_submit_twice_is_409(make_client):
    client = make_client()
    create(client, "t1")
    claimed_id(client, "alice")
    assert submit(client, "t1", "alice").status_code == 200
    assert submit(client, "t1", "alice").status_code == 409


def test_label_not_allowed_is_422_and_keeps_lease(make_client):
    client = make_client()
    create(client, "t1")
    claimed_id(client, "alice")
    assert submit(client, "t1", "alice", "fish").status_code == 422
    assert get(client, "t1")["state"] == "leased"
    assert submit(client, "t1", "alice", "bird").status_code == 200


def test_unknown_task_is_404(make_client):
    client = make_client()
    assert submit(client, "nope", "alice").status_code == 404
    assert client.get("/tasks/nope").status_code == 404


@pytest.mark.parametrize("headers", [{}, {"X-Annotator-Id": ""}, {"X-Annotator-Id": "   "}])
def test_missing_annotator_header_is_400(make_client, headers):
    client = make_client()
    create(client, "t1")
    assert client.post("/tasks/claim", headers=headers).status_code == 400
    assert client.post("/tasks/t1/extend", headers=headers).status_code == 400
    assert client.post("/tasks/t1/submit", json={"label": "cat"}, headers=headers).status_code == 400
    assert get(client, "t1")["state"] == "pending"


def test_annotator_header_is_stripped(make_client):
    client = make_client()
    create(client, "t1")
    claim(client, " alice ")
    assert get(client, "t1")["leases"][0]["annotator_id"] == "alice"
    assert submit(client, "t1", "alice").status_code == 200
