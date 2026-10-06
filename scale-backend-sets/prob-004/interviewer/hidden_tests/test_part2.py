"""Part 2: redundancy, concurrent leases per task, consensus. Gold tasks are the mid-part change."""

import pytest

from conftest import T0, claim, claimed_id, create, get, ids_in_state, submit


def label_task(client, task_id, votes):
    """Have one annotator per vote claim the task and submit, one after another."""
    for annotator, label in votes:
        assert claimed_id(client, annotator) == task_id
        assert submit(client, task_id, annotator, label).status_code == 200


def test_three_annotators_lease_one_task(make_client):
    client = make_client(redundancy=3)
    create(client, "t1")
    assert [claimed_id(client, a) for a in ("alice", "bob", "carol")] == ["t1"] * 3
    task = get(client, "t1")
    assert task["state"] == "leased"
    assert sorted(lease["annotator_id"] for lease in task["leases"]) == ["alice", "bob", "carol"]
    assert claim(client, "dave").status_code == 204


def test_slots_fill_oldest_first(make_client):
    client = make_client(redundancy=3)
    create(client, "t1", "t2")
    assert [claimed_id(client, a) for a in ("a1", "a2", "a3", "a4", "a5", "a6")] == ["t1"] * 3 + ["t2"] * 3
    assert claim(client, "a7").status_code == 204


def test_majority_completes(make_client, clock):
    client = make_client(redundancy=3)
    create(client, "t1")
    label_task(client, "t1", [("alice", "cat"), ("bob", "dog")])
    partial = get(client, "t1")
    assert partial["state"] == "pending"
    assert (partial["consensus_label"], partial["agreement"]) == (None, None)
    clock.advance(1)
    label_task(client, "t1", [("carol", "cat")])
    task = get(client, "t1")
    assert task["state"] == "completed"
    assert task["consensus_label"] == "cat"
    assert task["agreement"] == 0.67
    assert [(s["annotator_id"], s["label"]) for s in task["submissions"]] == [
        ("alice", "cat"), ("bob", "dog"), ("carol", "cat")]
    assert task["submissions"][2]["submitted_at"] == T0 + 1
    assert ids_in_state(client, "completed") == ["t1"]


def test_unanimous_agreement_is_one(make_client):
    client = make_client(redundancy=3)
    create(client, "t1")
    label_task(client, "t1", [("alice", "dog"), ("bob", "dog"), ("carol", "dog")])
    task = get(client, "t1")
    assert (task["state"], task["consensus_label"], task["agreement"]) == ("completed", "dog", 1.0)


def test_no_majority_is_disputed(make_client):
    client = make_client(redundancy=3)
    create(client, "t1")
    label_task(client, "t1", [("alice", "cat"), ("bob", "dog"), ("carol", "bird")])
    task = get(client, "t1")
    assert (task["state"], task["consensus_label"], task["agreement"]) == ("disputed", None, 0.33)
    assert ids_in_state(client, "disputed") == ["t1"]


def test_final_task_is_not_claimable_or_submittable(make_client):
    client = make_client(redundancy=3)
    create(client, "t1")
    label_task(client, "t1", [("alice", "cat"), ("bob", "cat"), ("carol", "dog")])
    assert claim(client, "dave").status_code == 204
    assert submit(client, "t1", "dave").status_code == 409
    assert submit(client, "t1", "alice").status_code == 409


def test_submitter_never_gets_task_again(make_client, clock):
    client = make_client(redundancy=3)
    create(client, "t1", "t2")
    label_task(client, "t1", [("alice", "cat")])
    assert claimed_id(client, "alice") == "t2"
    assert submit(client, "t2", "alice").status_code == 200
    clock.advance(600)
    assert claim(client, "alice").status_code == 204
    assert claimed_id(client, "bob") == "t1"


def test_submitter_cannot_submit_twice(make_client):
    client = make_client(redundancy=3)
    create(client, "t1")
    label_task(client, "t1", [("alice", "cat")])
    assert submit(client, "t1", "alice", "dog").status_code == 409
    assert len(get(client, "t1")["submissions"]) == 1


def test_submission_and_leases_share_slots(make_client, clock):
    client = make_client(redundancy=3)
    create(client, "t1", "t2")
    label_task(client, "t1", [("alice", "cat")])
    assert claimed_id(client, "bob") == "t1"
    assert claimed_id(client, "carol") == "t1"
    assert claimed_id(client, "dave") == "t2"  # t1 has 1 submission + 2 live leases
    clock.advance(60)  # bob's and carol's leases expire, freeing two slots
    assert get(client, "t1")["state"] == "pending"
    assert claimed_id(client, "erin") == "t1"


def test_holder_claiming_again_gets_same_task(make_client, clock):
    client = make_client(redundancy=3)
    create(client, "t1", "t2")
    first = claim(client, "alice").json()
    clock.advance(10)
    again = claim(client, "alice").json()
    assert (again["id"], again["lease_expires_at"]) == ("t1", first["lease_expires_at"])
    assert len(get(client, "t1")["leases"]) == 1


def test_redundancy_one_is_unchanged(make_client):
    client = make_client()
    create(client, "t1")
    label_task(client, "t1", [("alice", "dog")])
    task = get(client, "t1")
    assert (task["state"], task["consensus_label"], task["agreement"]) == ("submitted", None, None)


@pytest.mark.change
def test_gold_accuracy_stats(make_client):
    client = make_client()
    create(client, "g1", gold_label="cat")
    create(client, "g2", "g3", gold_label="dog")
    create(client, "n1")
    for task_id, label in [("g1", "cat"), ("g2", "cat"), ("g3", "dog"), ("n1", "bird")]:
        label_task(client, task_id, [("alice", label)])
    stats = client.get("/annotators/alice/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert (body["gold_seen"], body["gold_correct"], body["accuracy"]) == (3, 2, 0.67)


@pytest.mark.change
def test_gold_stats_with_redundancy(make_client):
    client = make_client(redundancy=3)
    create(client, "g1", gold_label="cat")
    label_task(client, "g1", [("alice", "cat"), ("bob", "dog"), ("carol", "cat")])
    stats = {a: client.get(f"/annotators/{a}/stats").json() for a in ("alice", "bob")}
    assert (stats["alice"]["gold_seen"], stats["alice"]["gold_correct"], stats["alice"]["accuracy"]) == (1, 1, 1.0)
    assert (stats["bob"]["gold_seen"], stats["bob"]["gold_correct"], stats["bob"]["accuracy"]) == (1, 0, 0.0)


@pytest.mark.change
def test_gold_stats_for_unknown_annotator(make_client):
    body = make_client().get("/annotators/nobody/stats").json()
    assert (body["gold_seen"], body["gold_correct"], body["accuracy"]) == (0, 0, None)


@pytest.mark.change
def test_claim_does_not_reveal_gold_label(make_client):
    client = make_client()
    create(client, "g1", gold_label="cat")
    resp = claim(client, "alice")
    assert resp.json()["id"] == "g1"
    body = resp.json()
    assert "gold_label" not in body
    assert "cat" not in [value for key, value in body.items() if key != "labels"]


@pytest.mark.change
def test_gold_label_must_be_allowed(make_client):
    client = make_client()
    resp = client.post("/tasks", json={"tasks": [
        {"id": "g1", "data": {}, "labels": ["cat", "dog"], "gold_label": "fish"},
        {"id": "g2", "data": {}, "labels": ["cat", "dog"], "gold_label": "dog"},
    ]})
    assert resp.status_code == 201
    assert resp.json()["created"] == ["g2"]
    assert [e["index"] for e in resp.json()["errors"]] == [0]
    assert client.get("/tasks/g1").status_code == 404

