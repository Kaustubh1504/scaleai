"""Part 3: versions and compare-and-set reviews, concurrency, idempotent re-runs, self-consistency."""

import json

import pytest

from conftest import (EXPECTED_STATUS, IDS, REVIEW_IDS, CountingLLM, LLMConfig, MockLLMClient, all_audit,
                      batch_content, classify, doc_audit, get_doc, make_llm, review, run_at_once, upload)
from shared.mock_llm import FunctionResponder

REVIEWERS = [f"r{i}" for i in range(8)]


# --- versions ----------------------------------------------------------------------------------------

def test_version_counts_status_changes(make_client):
    client = make_client()
    batch_id = upload(client)
    assert {get_doc(client, d)["version"] for d in IDS} == {1}
    classify(client, batch_id)
    assert {get_doc(client, d)["version"] for d in IDS} == {2}
    assert review(client, "D-003", label="id_document").json()["version"] == 3
    assert get_doc(client, "D-003")["version"] == 3
    assert [item["version"] for item in client.get("/review-queue").json()["items"]] == [2, 2]


def test_stale_expected_version_is_409(make_client):
    client = make_client()
    classify(client, upload(client))
    before = all_audit(client)
    for stale in (1, 3):
        assert review(client, "D-003", label="id_document", expected_version=stale).status_code == 409
    assert get_doc(client, "D-003")["status"] == "needs_review"
    assert all_audit(client) == before
    resp = review(client, "D-003", label="id_document", expected_version=2)
    assert resp.status_code == 200, resp.text
    assert review(client, "D-003", label="id_document", expected_version=3).status_code == 409


# --- concurrent reviews --------------------------------------------------------------------------------

def test_concurrent_reviews_have_exactly_one_winner(make_client):
    client = make_client()
    classify(client, upload(client))
    for doc_id in REVIEW_IDS:
        responses = run_at_once(
            lambda reviewer, doc_id=doc_id: review(client, doc_id, reviewer=reviewer, label="invoice",
                                                   reason=f"{reviewer} says invoice"),
            [(r,) for r in REVIEWERS])
        codes = [r.status_code for r in responses]
        assert sorted(codes) == [200] + [409] * (len(REVIEWERS) - 1), codes
        winner = REVIEWERS[codes.index(200)]
        doc = get_doc(client, doc_id)
        assert (doc["status"], doc["reviewed_by"], doc["version"]) == ("reviewed", winner, 3)
        reviewed = [e for e in doc_audit(client, doc_id) if e["action"] == "reviewed"]
        assert [e["actor"] for e in reviewed] == [winner]


def test_concurrent_reviews_with_same_expected_version(make_client):
    client = make_client()
    classify(client, upload(client))
    responses = run_at_once(
        lambda reviewer: review(client, "D-005", reviewer=reviewer, label="other", expected_version=2),
        [(r,) for r in REVIEWERS])
    assert sorted(r.status_code for r in responses) == [200] + [409] * (len(REVIEWERS) - 1)
    assert len([e for e in doc_audit(client, "D-005") if e["action"] == "reviewed"]) == 1


# --- idempotent re-runs ----------------------------------------------------------------------------------

def test_rerun_does_not_touch_routed_or_reviewed_documents(make_client, clock):
    llm = CountingLLM(make_llm(LLMConfig(prompt_faults={"Ref D-002": ["malformed"] * 3}), clock))
    client = make_client(llm=llm)
    batch_id = upload(client)
    classify(client, batch_id)
    assert get_doc(client, "D-002")["review_reason"] == "classification_failed"
    assert review(client, "D-003", label="other", reason="not a real passport").status_code == 200
    docs_before = {d: get_doc(client, d) for d in IDS}
    events_before = all_audit(client)
    calls_before = llm.calls

    clock.advance(30)
    again = classify(client, batch_id)
    assert llm.calls == calls_before
    assert (again["classified"], again["failed"]) == (0, 0)
    assert {d["doc_id"]: d for d in again["documents"]} == docs_before
    assert {d: get_doc(client, d) for d in IDS} == docs_before
    assert all_audit(client) == events_before

    restarted = make_client(llm=llm)
    classify(restarted, batch_id)
    assert llm.calls == calls_before
    assert all_audit(restarted) == events_before


def test_rerun_classifies_only_new_documents(make_client, clock):
    llm = CountingLLM(make_llm(clock=clock))
    client = make_client(llm=llm)
    first = classify(client, upload(client))
    assert (first["classified"], first["failed"]) == (len(IDS), 0)
    assert llm.calls == len(IDS)
    second_batch = upload(client, batch_content("E"))
    body = classify(client, second_batch)
    assert (body["classified"], body["failed"]) == (len(IDS), 0)
    assert llm.calls == 2 * len(IDS)
    assert [d["doc_id"] for d in body["documents"]] == [d.replace("D-", "E-") for d in IDS]
    assert {d["doc_id"]: d["status"] for d in body["documents"]} == {
        d.replace("D-", "E-"): status for d, status in EXPECTED_STATUS.items()}
    assert classify(client, second_batch)["classified"] == 0
    assert llm.calls == 2 * len(IDS)


def test_concurrent_classify_records_each_document_once(make_client, clock):
    llm = CountingLLM(make_llm(clock=clock), hold_s=0.005)
    client = make_client(llm=llm)
    batch_id = upload(client)
    responses = run_at_once(lambda: client.post(f"/batches/{batch_id}/classify"), [()] * 4)
    assert [r.status_code for r in responses] == [200] * 4
    for doc_id in IDS:
        actions = [e["action"] for e in doc_audit(client, doc_id)]
        routing = "auto_accepted" if EXPECTED_STATUS[doc_id] == "auto_accepted" else "routed_to_review"
        assert actions == ["ingested", "classified", routing], (doc_id, actions)
        assert get_doc(client, doc_id)["version"] == 2


# --- self-consistency -------------------------------------------------------------------------------

def test_two_samples_per_document(make_client, clock):
    llm = CountingLLM(make_llm(clock=clock))
    client = make_client(llm=llm, consistency_samples=2)
    body = classify(client, upload(client))
    assert {d["doc_id"]: d["status"] for d in body["documents"]} == EXPECTED_STATUS
    assert all(llm.calls_for(doc_id) == 2 for doc_id in IDS)
    assert get_doc(client, "D-001")["classification"]["attempts"] == 2


def test_default_is_one_sample(make_client, clock):
    llm = CountingLLM(make_llm(clock=clock))
    client = make_client(llm=llm)
    body = classify(client, upload(client))
    assert all(llm.calls_for(doc_id) == 1 for doc_id in IDS)
    assert {d["doc_id"]: d["status"] for d in body["documents"]} == EXPECTED_STATUS
    assert get_doc(client, "D-001")["classification"]["attempts"] == 1


def test_disagreement_goes_to_review(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"Ref D-001": ["ok", "inconsistent"]}), clock)
    client = make_client(llm=llm, consistency_samples=2)
    classify(client, upload(client))
    doc = get_doc(client, "D-001")
    assert (doc["status"], doc["review_reason"], doc["final_label"]) == ("needs_review", "disagreement", None)
    assert doc["classification"]["label"] == "contract"
    assert doc_audit(client, "D-001")[-1]["details"]["review_reason"] == "disagreement"
    assert get_doc(client, "D-004")["status"] == "auto_accepted"
    assert "D-001" in [item["doc_id"] for item in client.get("/review-queue").json()["items"]]


def test_lower_confidence_of_two_samples_is_used(make_client, clock):
    def answer(ctx):
        return json.dumps({"label": "invoice", "confidence": 0.9 if ctx.attempt == 1 else 0.7})

    content = b'{"doc_id": "S-1", "title": "file-s1.pdf", "text": "Invoice for March."}\n'
    client = make_client(llm=MockLLMClient(responder=FunctionResponder(answer), clock=clock), consistency_samples=2)
    classify(client, upload(client, content))
    doc = get_doc(client, "S-1")
    assert doc["classification"]["confidence"] == 0.7
    assert (doc["status"], doc["review_reason"]) == ("needs_review", "low_confidence")


def test_attempts_are_summed_across_samples(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"Ref D-004": ["server_error", "ok", "timeout"]}), clock)
    client = make_client(llm=llm, consistency_samples=2)
    classify(client, upload(client))
    doc = get_doc(client, "D-004")
    assert doc["classification"]["attempts"] == 4
    assert doc["status"] == "auto_accepted"


def test_failed_first_sample_skips_the_second(make_client, clock):
    llm = CountingLLM(make_llm(LLMConfig(prompt_faults={"Ref D-004": ["malformed"] * 3}), clock))
    client = make_client(llm=llm, consistency_samples=2)
    classify(client, upload(client))
    doc = get_doc(client, "D-004")
    assert llm.calls_for("D-004") == 3
    assert doc["classification"]["attempts"] == 3
    assert (doc["status"], doc["review_reason"]) == ("needs_review", "classification_failed")


def test_failed_second_sample_fails_the_document(make_client, clock):
    llm = make_llm(LLMConfig(prompt_faults={"Ref D-004": ["ok", "malformed", "malformed", "malformed"]}), clock)
    client = make_client(llm=llm, consistency_samples=2)
    classify(client, upload(client))
    doc = get_doc(client, "D-004")
    assert (doc["classification"]["label"], doc["classification"]["confidence"]) == (None, None)
    assert doc["classification"]["attempts"] == 4
    assert doc["classification"]["error"]
    assert doc["review_reason"] == "classification_failed"


@pytest.mark.parametrize("samples", [0, 3])
def test_invalid_sample_count_is_rejected(make_client, samples):
    with pytest.raises(ValueError):
        make_client(consistency_samples=samples)
