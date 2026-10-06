"""API tests for routing, the review queue, the audit trail and the Part 3 hardening."""

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import LLMConfig

DATA = Path(__file__).resolve().parent.parent / "data"
T0 = 1_700_000_000.0
# With the real keyword classifier (see mock_services/llm.py) and the default 0.8 threshold.
SAMPLE_REVIEW = ["DOC-1004", "DOC-1005", "DOC-1006", "DOC-1008", "DOC-1011", "DOC-1012"]


@pytest.fixture
def clock():
    return FakeClock(start=T0)


@pytest.fixture
def make_client(tmp_path, clock):
    def build(config: LLMConfig | None = None, **kwargs) -> TestClient:
        llm = make_llm(config or LLMConfig(seed=1), clock=clock)
        return TestClient(create_app(storage_dir=tmp_path, llm=llm, clock=clock, **kwargs))

    return build


def load_sample(client) -> str:
    content = (DATA / "documents.jsonl").read_bytes()
    batch_id = client.post("/batches", files={"file": ("documents.jsonl", content, "x")}).json()["batch_id"]
    assert client.post(f"/batches/{batch_id}/classify").status_code == 200
    return batch_id


def review(client, doc_id, **body):
    return client.post(f"/documents/{doc_id}/review", json={"reviewer": "alice", **body})


def actions(client, doc_id):
    return [e["action"] for e in client.get(f"/documents/{doc_id}/audit").json()["events"]]


def test_sample_routing(make_client):
    client = make_client()
    load_sample(client)
    queue = client.get("/review-queue").json()["items"]
    assert [d["doc_id"] for d in queue] == SAMPLE_REVIEW
    assert {d["doc_id"]: d["review_reason"] for d in queue}["DOC-1006"] == "low_confidence"
    doc = client.get("/documents/DOC-1001").json()
    assert (doc["status"], doc["final_label"], doc["version"]) == ("auto_accepted", "contract", 2)


def test_review_flow_and_trail(make_client, clock):
    client = make_client()
    load_sample(client)
    clock.advance(30)
    resp = review(client, "DOC-1006", label="contract", expected_version=2)
    assert resp.status_code == 200
    assert (resp.json()["status"], resp.json()["final_label"], resp.json()["version"]) == ("reviewed", "contract", 3)
    assert actions(client, "DOC-1006") == ["ingested", "classified", "routed_to_review", "reviewed"]
    event = client.get("/audit", params={"actor": "alice"}).json()["events"]
    assert [(e["doc_id"], e["ts"], e["details"]) for e in event] == [
        ("DOC-1006", T0 + 30, {"label": "contract", "model_label": "contract", "reason": None})]


@pytest.mark.parametrize("body, status", [
    ({"label": "invoice"}, 422),                       # override without a reason
    ({"label": "invoice", "reason": "  "}, 422),       # blank reason
    ({"label": "Invoice", "reason": "r"}, 422),        # labels are exact
    ({"label": "contract", "expected_version": 1}, 409),
])
def test_rejected_reviews_change_nothing(make_client, body, status):
    client = make_client()
    load_sample(client)
    before = client.get("/audit").json()["events"]
    assert review(client, "DOC-1006", **body).status_code == status
    assert client.get("/documents/DOC-1006").json()["status"] == "needs_review"
    assert client.get("/audit").json()["events"] == before


def test_review_of_final_document_is_409(make_client):
    client = make_client()
    load_sample(client)
    assert review(client, "DOC-1001", label="contract").status_code == 409
    assert review(client, "missing", label="contract").status_code == 404


def test_audit_filters_validate(make_client):
    client = make_client()
    load_sample(client)
    assert client.get("/audit", params={"action": "nope"}).status_code == 422
    assert client.get("/audit", params={"since": "soon"}).status_code == 422
    assert len(client.get("/audit", params={"action": "ingested"}).json()["events"]) == 12


def test_audit_table_is_append_only(make_client, tmp_path):
    client = make_client()
    load_sample(client)
    conn = sqlite3.connect(tmp_path / "intake.db")
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE audit_events SET actor = 'mallory'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM audit_events")
    finally:
        conn.close()


def test_restart_keeps_trail_and_seq(make_client):
    client = make_client()
    load_sample(client)
    before = client.get("/audit").json()["events"]
    restarted = make_client()
    line = b'{"doc_id": "NEW-1", "title": "n.pdf", "text": "Invoice total due $5."}\n'
    restarted.post("/batches", files={"file": ("n.jsonl", line, "x")})
    after = restarted.get("/audit").json()["events"]
    assert after[: len(before)] == before
    assert after[-1]["seq"] > before[-1]["seq"]


def test_rerun_is_a_no_op(make_client):
    client = make_client()
    batch_id = load_sample(client)
    assert review(client, "DOC-1005", label="other").status_code == 200
    before = client.get("/audit").json()["events"]
    body = client.post(f"/batches/{batch_id}/classify").json()
    assert (body["classified"], body["failed"]) == (0, 0)
    assert client.get("/audit").json()["events"] == before
    assert client.get("/documents/DOC-1005").json()["status"] == "reviewed"


def test_concurrent_reviews_one_winner(make_client):
    client = make_client()
    load_sample(client)
    barrier = threading.Barrier(6)

    def go(reviewer):
        barrier.wait()
        return client.post("/documents/DOC-1011/review", json={"reviewer": reviewer, "label": "other"}).status_code

    with ThreadPoolExecutor(6) as pool:
        codes = list(pool.map(go, [f"r{i}" for i in range(6)]))
    assert sorted(codes) == [200] + [409] * 5
    assert actions(client, "DOC-1011").count("reviewed") == 1


def test_disagreement_with_two_samples(make_client):
    client = make_client(LLMConfig(seed=1, prompt_faults={"Okafor": ["ok", "inconsistent"]}), consistency_samples=2)
    load_sample(client)
    doc = client.get("/documents/DOC-1003").json()
    assert (doc["status"], doc["review_reason"], doc["classification"]["attempts"]) == (
        "needs_review", "disagreement", 2)


@pytest.mark.parametrize("kwargs", [{"auto_accept_threshold": 1.5}, {"consistency_samples": 3}])
def test_bad_settings(tmp_path, kwargs):
    with pytest.raises(ValueError):
        create_app(storage_dir=tmp_path, llm=make_llm(), clock=FakeClock(), **kwargs)
