"""Part 1: confidence routing, the review queue, and resolving reviews."""

import pytest

from conftest import (EXPECTED_STATUS, IDS, MODEL_LABEL, REVIEW_IDS, LLMConfig, batch_content, classify, get_doc,
                      make_llm, review, upload)

LABELS = ["contract", "invoice", "id_document", "support_letter", "other"]


def queue_ids(client):
    resp = client.get("/review-queue")
    assert resp.status_code == 200, resp.text
    return [item["doc_id"] for item in resp.json()["items"]]


def test_uploaded_documents_start_ingested(make_client):
    client = make_client()
    upload(client)
    for doc_id in IDS:
        doc = get_doc(client, doc_id)
        assert doc["doc_id"] == doc_id
        assert (doc["status"], doc["final_label"], doc["review_reason"], doc["reviewed_by"]) == (
            "ingested", None, None, None)
        assert doc["classification"] is None
    assert queue_ids(client) == []


def test_routing_by_confidence(make_client):
    client = make_client()
    body = classify(client, upload(client))
    assert {d["doc_id"]: d["status"] for d in body["documents"]} == EXPECTED_STATUS
    for doc_id in IDS:
        doc = get_doc(client, doc_id)
        assert doc["status"] == EXPECTED_STATUS[doc_id]
        assert doc["classification"]["label"] == MODEL_LABEL[doc_id]
        if doc["status"] == "auto_accepted":
            assert (doc["final_label"], doc["review_reason"]) == (MODEL_LABEL[doc_id], None)
        else:
            assert (doc["final_label"], doc["review_reason"]) == (None, "low_confidence")


def test_confidence_equal_to_threshold_is_auto_accepted(make_client):
    client = make_client()
    classify(client, upload(client))
    doc = get_doc(client, "D-002")
    assert doc["classification"]["confidence"] == 0.80
    assert (doc["status"], doc["final_label"]) == ("auto_accepted", "invoice")
    assert get_doc(client, "D-003")["status"] == "needs_review"  # 0.79


def test_batch_view_shows_status(make_client):
    client = make_client()
    batch_id = upload(client)
    assert {d["status"] for d in client.get(f"/batches/{batch_id}").json()["documents"]} == {"ingested"}
    classify(client, batch_id)
    docs = client.get(f"/batches/{batch_id}").json()["documents"]
    assert {d["doc_id"]: d["status"] for d in docs} == EXPECTED_STATUS


@pytest.mark.parametrize("threshold, auto", [
    (0.5, {"D-001", "D-002", "D-003", "D-004", "D-006"}),
    (0.96, set()),
    (0.0, set(IDS)),
])
def test_threshold_is_configurable(make_client, threshold, auto):
    client = make_client(auto_accept_threshold=threshold)
    body = classify(client, upload(client))
    assert {d["doc_id"] for d in body["documents"] if d["status"] == "auto_accepted"} == auto
    assert {d["doc_id"] for d in body["documents"] if d["status"] == "needs_review"} == set(IDS) - auto


def test_failed_classification_goes_to_review(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(prompt_faults={"Ref D-002": ["malformed"] * 3}), clock))
    classify(client, upload(client))
    doc = get_doc(client, "D-002")
    assert (doc["status"], doc["final_label"], doc["review_reason"]) == ("needs_review", None, "classification_failed")
    assert doc["classification"]["label"] is None and doc["classification"]["error"]
    assert "D-002" in queue_ids(client)


def test_non_retryable_failure_goes_to_review(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(max_context_tokens=5), clock))
    classify(client, upload(client))
    assert {get_doc(client, d)["review_reason"] for d in IDS} == {"classification_failed"}


def test_review_queue_contains_only_needs_review_in_order(make_client, clock):
    client = make_client()
    first = upload(client, batch_content("D"))
    second = upload(client, batch_content("E"))
    classify(client, second)  # E-* enter the queue first
    clock.advance(10)
    classify(client, first)
    expected = [d.replace("D-", "E-") for d in REVIEW_IDS] + REVIEW_IDS
    assert queue_ids(client) == expected
    items = client.get("/review-queue").json()["items"]
    assert all(item["status"] == "needs_review" for item in items)
    assert items[0]["classification"]["label"] == "id_document"
    assert items[0]["review_reason"] == "low_confidence"


def test_review_resolves_document(make_client):
    client = make_client()
    classify(client, upload(client))
    resp = review(client, "D-003", reviewer="alice", label="id_document")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["doc_id"] == "D-003"
    assert (body["status"], body["final_label"], body["reviewed_by"]) == ("reviewed", "id_document", "alice")
    assert body["review_reason"] == "low_confidence"
    assert body["classification"]["label"] == "id_document"
    assert get_doc(client, "D-003") == body
    assert queue_ids(client) == ["D-005", "D-006"]


def test_reviewer_may_override_the_model(make_client):
    client = make_client()
    classify(client, upload(client))
    resp = review(client, "D-006", reviewer="  bob ", label="invoice", reason="it is the invoice, not the contract")
    assert resp.status_code == 200, resp.text
    doc = get_doc(client, "D-006")
    assert (doc["status"], doc["final_label"], doc["reviewed_by"]) == ("reviewed", "invoice", "bob")
    assert doc["classification"]["label"] == "contract"


def test_review_failed_classification(make_client, clock):
    client = make_client(llm=make_llm(LLMConfig(prompt_faults={"Ref D-002": ["server_error"] * 3}), clock))
    classify(client, upload(client))
    resp = review(client, "D-002", label="invoice", reason="scanned invoice")
    assert resp.status_code == 200, resp.text
    assert (resp.json()["status"], resp.json()["final_label"]) == ("reviewed", "invoice")


def test_review_conflicts_are_409(make_client):
    client = make_client()
    upload(client)
    resp = review(client, "D-003", label="id_document")  # still ingested
    assert resp.status_code == 409
    assert isinstance(resp.json()["detail"], str) and resp.json()["detail"]

    classify(client, client.get("/documents/D-001").json()["batch_id"])
    assert review(client, "D-001", label="contract").status_code == 409  # auto_accepted
    assert get_doc(client, "D-001")["status"] == "auto_accepted"

    assert review(client, "D-003", label="id_document").status_code == 200
    again = review(client, "D-003", reviewer="bob", label="other", reason="second opinion")
    assert again.status_code == 409
    doc = get_doc(client, "D-003")
    assert (doc["final_label"], doc["reviewed_by"]) == ("id_document", "alice")


@pytest.mark.parametrize("body", [
    {"reviewer": "alice", "label": "Contract", "reason": "r"},
    {"reviewer": "alice", "label": "spam", "reason": "r"},
    {"reviewer": "alice", "label": "", "reason": "r"},
    {"reviewer": "alice", "reason": "r"},
    {"label": "id_document", "reason": "r"},
    {"reviewer": "   ", "label": "id_document", "reason": "r"},
    {"reviewer": "", "label": "id_document", "reason": "r"},
])
def test_invalid_review_body_is_422(make_client, body):
    client = make_client()
    classify(client, upload(client))
    assert client.post("/documents/D-003/review", json=body).status_code == 422
    doc = get_doc(client, "D-003")
    assert (doc["status"], doc["final_label"], doc["reviewed_by"]) == ("needs_review", None, None)


def test_every_label_is_accepted(make_client):
    client = make_client(auto_accept_threshold=1.0)
    classify(client, upload(client))
    for doc_id, label in zip(IDS, LABELS):
        resp = review(client, doc_id, label=label, reason="checked")
        assert resp.status_code == 200, resp.text
        assert resp.json()["final_label"] == label


def test_unknown_document_is_404(make_client):
    client = make_client()
    classify(client, upload(client))
    assert get_doc(client, "D-001")["status"] == "auto_accepted"
    assert client.get("/documents/nope").status_code == 404
    assert review(client, "nope", label="other").status_code == 404


def test_statuses_and_queue_survive_restart(make_client):
    client = make_client()
    classify(client, upload(client))
    assert review(client, "D-003", label="id_document").status_code == 200
    restarted = make_client()
    assert get_doc(restarted, "D-001")["status"] == "auto_accepted"
    assert get_doc(restarted, "D-003")["status"] == "reviewed"
    assert queue_ids(restarted) == ["D-005", "D-006"]
