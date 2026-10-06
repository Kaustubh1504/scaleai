"""Part 2: the audit trail (events, endpoints, filters, durability) and the override-reason change."""

import pytest

from conftest import (EXPECTED_STATUS, IDS, T0, LLMConfig, all_audit, batch_content, classify, doc_audit, get_doc,
                      make_llm, review, upload)

EVENT_KEYS = {"seq", "ts", "doc_id", "actor", "action", "from_status", "to_status", "details"}


def assert_seqs_increase(events):
    seqs = [e["seq"] for e in events]
    assert all(isinstance(s, int) and s > 0 for s in seqs)
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_ingested_events(make_client):
    client = make_client()
    batch_id = upload(client)
    for doc_id in IDS:
        events = doc_audit(client, doc_id)
        assert len(events) == 1
        event = events[0]
        assert EVENT_KEYS <= set(event)
        assert (event["doc_id"], event["actor"], event["action"]) == (doc_id, "system", "ingested")
        assert (event["from_status"], event["to_status"]) == (None, "ingested")
        assert event["ts"] == T0
        assert event["details"]["batch_id"] == batch_id


def test_rejected_rows_have_no_events(make_client):
    client = make_client()
    content = batch_content() + b'{"doc_id": "BAD-1", "title": "x.pdf", "text": ""}\n'
    upload(client, content)
    assert len(all_audit(client)) == len(IDS)
    assert client.get("/documents/BAD-1/audit").status_code == 404


def test_auto_accepted_trail(make_client, clock):
    client = make_client()
    batch_id = upload(client)
    clock.advance(5)
    classify(client, batch_id)
    events = doc_audit(client, "D-001")
    assert [e["action"] for e in events] == ["ingested", "classified", "auto_accepted"]
    classified, accepted = events[1], events[2]
    assert (classified["from_status"], classified["to_status"]) == ("ingested", "ingested")
    assert classified["details"]["label"] == "contract"
    assert classified["details"]["confidence"] == 0.95
    assert classified["details"]["attempts"] == 1
    assert classified["details"]["error"] is None
    assert (accepted["from_status"], accepted["to_status"]) == ("ingested", "auto_accepted")
    assert accepted["details"]["final_label"] == "contract"
    assert accepted["details"]["confidence"] == 0.95
    assert all(e["actor"] == "system" for e in events)
    assert [e["ts"] for e in events] == [T0, T0 + 5, T0 + 5]
    assert_seqs_increase(events)


def test_routed_to_review_trail(make_client):
    client = make_client()
    classify(client, upload(client))
    events = doc_audit(client, "D-005")
    assert [e["action"] for e in events] == ["ingested", "classified", "routed_to_review"]
    assert events[1]["details"]["label"] == "other"
    assert (events[2]["from_status"], events[2]["to_status"]) == ("ingested", "needs_review")
    assert events[2]["details"]["review_reason"] == "low_confidence"


def test_failed_classification_trail(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(prompt_faults={"Ref D-002": ["timeout"] * 3}), clock))
    classify(client, upload(client))
    events = doc_audit(client, "D-002")
    assert [e["action"] for e in events] == ["ingested", "classified", "routed_to_review"]
    details = events[1]["details"]
    assert (details["label"], details["confidence"], details["attempts"]) == (None, None, 3)
    assert isinstance(details["error"], str) and details["error"]
    assert events[2]["details"]["review_reason"] == "classification_failed"


def test_reviewed_event(make_client, clock):
    client = make_client()
    classify(client, upload(client))
    clock.advance(60)
    assert review(client, "D-006", reviewer=" carol ", label="invoice", reason="line items").status_code == 200
    event = doc_audit(client, "D-006")[-1]
    assert (event["action"], event["actor"]) == ("reviewed", "carol")
    assert (event["from_status"], event["to_status"]) == ("needs_review", "reviewed")
    assert event["ts"] == T0 + 60
    assert event["details"]["label"] == "invoice"
    assert event["details"]["model_label"] == "contract"


def test_reviewed_event_without_model_label(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(prompt_faults={"Ref D-002": ["malformed"] * 3}), clock))
    classify(client, upload(client))
    assert review(client, "D-002", label="invoice", reason="manual").status_code == 200
    event = doc_audit(client, "D-002")[-1]
    assert event["action"] == "reviewed"
    assert event["details"]["model_label"] is None


def test_rejected_requests_append_nothing(make_client):
    client = make_client()
    classify(client, upload(client))
    before = all_audit(client)
    assert review(client, "D-001", label="contract", reason="r").status_code == 409
    assert review(client, "D-003", label="Passport", reason="r").status_code == 422
    assert review(client, "D-003", reviewer=" ", label="id_document", reason="r").status_code == 422
    assert review(client, "nope", label="other", reason="r").status_code == 404
    assert all_audit(client) == before


def test_global_audit_order_and_count(make_client):
    client = make_client()
    classify(client, upload(client))
    assert review(client, "D-003", label="id_document").status_code == 200
    events = all_audit(client)
    assert len(events) == len(IDS) * 3 + 1
    assert_seqs_increase(events)
    assert all(EVENT_KEYS <= set(e) for e in events)
    for doc_id in IDS:
        assert doc_audit(client, doc_id) == [e for e in events if e["doc_id"] == doc_id]


def test_classified_event_comes_right_before_its_routing_event(make_client):
    client = make_client()
    classify(client, upload(client))
    for doc_id in IDS:
        actions = [e["action"] for e in doc_audit(client, doc_id)]
        routing = "auto_accepted" if EXPECTED_STATUS[doc_id] == "auto_accepted" else "routed_to_review"
        assert actions == ["ingested", "classified", routing]


def test_events_are_immutable(make_client, clock):
    client = make_client()
    batch_id = upload(client)
    snapshot = all_audit(client)
    clock.advance(1)
    classify(client, batch_id)
    assert review(client, "D-005", label="other").status_code == 200
    later = all_audit(client)
    assert later[: len(snapshot)] == snapshot
    assert len(later) > len(snapshot)


def test_audit_filters(make_client, clock):
    client = make_client()
    batch_id = upload(client)
    clock.advance(10)
    classify(client, batch_id)
    clock.advance(10)
    assert review(client, "D-003", reviewer="alice", label="id_document").status_code == 200
    assert review(client, "D-005", reviewer="bob", label="other").status_code == 200

    alice = all_audit(client, actor="alice")
    assert [(e["doc_id"], e["action"]) for e in alice] == [("D-003", "reviewed")]
    assert all_audit(client, actor="nobody") == []

    routed = all_audit(client, action="routed_to_review")
    assert [e["doc_id"] for e in routed] == ["D-003", "D-005", "D-006"]
    assert len(all_audit(client, action="ingested")) == len(IDS)

    recent = all_audit(client, since=T0 + 20)
    assert [(e["doc_id"], e["actor"]) for e in recent] == [("D-003", "alice"), ("D-005", "bob")]
    assert len(all_audit(client, since=T0 + 10)) == len(IDS) * 2 + 2
    assert len(all_audit(client, since=T0)) == len(IDS) * 3 + 2

    both = all_audit(client, actor="system", action="auto_accepted", since=T0 + 10)
    assert [e["doc_id"] for e in both] == ["D-001", "D-002", "D-004"]
    assert all_audit(client, actor="bob", action="ingested") == []


@pytest.mark.parametrize("params", [{"action": "deleted"}, {"since": "yesterday"}])
def test_bad_audit_filters_are_422(make_client, params):
    client = make_client()
    upload(client)
    assert client.get("/audit", params=params).status_code == 422


def test_unknown_document_audit_is_404(make_client):
    client = make_client()
    upload(client)
    assert len(doc_audit(client, "D-001")) == 1
    assert client.get("/documents/nope/audit").status_code == 404


def test_audit_survives_restart_and_seq_keeps_increasing(make_client):
    client = make_client()
    classify(client, upload(client))
    assert review(client, "D-003", label="id_document").status_code == 200
    before = all_audit(client)

    restarted = make_client()
    assert all_audit(restarted) == before
    assert doc_audit(restarted, "D-003") == [e for e in before if e["doc_id"] == "D-003"]
    upload(restarted, batch_content("E"))
    after = all_audit(restarted)
    assert after[: len(before)] == before
    new = after[len(before):]
    assert len(new) == len(IDS)
    assert min(e["seq"] for e in new) > max(e["seq"] for e in before)
    assert_seqs_increase(after)


# --- mid-part change: overriding the model requires a reason ----------------------------------------

@pytest.mark.change
def test_override_without_reason_is_422(make_client):
    client = make_client()
    classify(client, upload(client))
    before = all_audit(client)
    assert review(client, "D-006", label="invoice").status_code == 422
    assert review(client, "D-006", label="invoice", reason="   ").status_code == 422
    assert review(client, "D-006", label="invoice", reason=None).status_code == 422
    assert get_doc(client, "D-006")["status"] == "needs_review"
    assert all_audit(client) == before


@pytest.mark.change
def test_override_reason_is_stored_trimmed(make_client):
    client = make_client()
    classify(client, upload(client))
    resp = review(client, "D-006", label="invoice", reason="  totals and tax lines  ")
    assert resp.status_code == 200, resp.text
    assert resp.json()["final_label"] == "invoice"
    assert doc_audit(client, "D-006")[-1]["details"]["reason"] == "totals and tax lines"


@pytest.mark.change
def test_agreeing_needs_no_reason(make_client):
    client = make_client()
    classify(client, upload(client))
    assert review(client, "D-006", label="contract").status_code == 200
    assert doc_audit(client, "D-006")[-1]["details"]["reason"] is None
    assert review(client, "D-005", label="other", reason="obviously a newsletter").status_code == 200
    assert doc_audit(client, "D-005")[-1]["details"]["reason"] == "obviously a newsletter"


@pytest.mark.change
def test_no_model_label_needs_no_reason(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(prompt_faults={"Ref D-002": ["malformed"] * 3}), clock))
    classify(client, upload(client))
    assert review(client, "D-002", label="invoice").status_code == 200
    assert doc_audit(client, "D-002")[-1]["details"]["reason"] is None


@pytest.mark.change
def test_reason_rule_comes_after_status_check(make_client):
    client = make_client()
    classify(client, upload(client))
    assert review(client, "D-001", label="invoice").status_code == 409  # auto_accepted: 409, not 422
