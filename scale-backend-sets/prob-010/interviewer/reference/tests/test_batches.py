"""Tests for the existing endpoints. Add your own next to these."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import LLMConfig

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def clock():
    return FakeClock(start=1_700_000_000)


@pytest.fixture
def make_client(tmp_path, clock):
    def build(config: LLMConfig | None = None, **kwargs) -> TestClient:
        llm = make_llm(config or LLMConfig(seed=1), clock=clock)
        return TestClient(create_app(storage_dir=tmp_path, llm=llm, clock=clock, **kwargs))

    return build


def upload(client, name, content=None):
    content = (DATA / name).read_bytes() if content is None else content
    return client.post("/batches", files={"file": (name, content, "application/octet-stream")})


def test_health(make_client):
    assert make_client().get("/health").json()["status"] == "ok"


def test_upload_jsonl_reports_bad_rows(make_client):
    resp = upload(make_client(), "documents.jsonl")
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_rows"] == 19
    assert len(body["accepted"]) == 12
    assert [e["row"] for e in body["errors"]] == [5, 7, 9, 10, 12, 13, 16]


def test_upload_csv(make_client):
    body = upload(make_client(), "documents.csv").json()
    assert body["accepted"] == ["CSV-2001", "CSV-2002", "CSV-2005", "CSV-2006", "CSV-2008"]
    assert [e["row"] for e in body["errors"]] == [3, 4, 7]


@pytest.mark.parametrize("name, content, status", [
    ("docs.txt", b"x", 415),
    ("docs.jsonl", b"", 400),
    ("documents_bad_header.csv", None, 400),
])
def test_unusable_files(make_client, name, content, status):
    assert upload(make_client(), name, content).status_code == status


def test_doc_ids_are_unique_across_batches(make_client):
    client = make_client()
    line = b'{"doc_id": "X-1", "title": "a.pdf", "text": "hello"}\n'
    assert upload(client, "a.jsonl", line).json()["accepted"] == ["X-1"]
    second = upload(client, "b.jsonl", line).json()
    assert second["accepted"] == []
    assert second["errors"][0]["row"] == 1


def test_classify_batch(make_client):
    client = make_client()
    batch_id = upload(client, "documents.jsonl").json()["batch_id"]
    resp = client.post(f"/batches/{batch_id}/classify")
    assert resp.status_code == 200
    body = resp.json()
    assert (body["classified"], body["failed"]) == (12, 0)
    labels = {d["doc_id"]: d["classification"]["label"] for d in body["documents"]}
    assert labels["DOC-1001"] == "contract"
    assert labels["DOC-1002"] == "invoice"
    assert labels["DOC-1011"] == "other"
    assert client.get(f"/batches/{batch_id}").json()["documents"] == body["documents"]


def test_unknown_batch_is_404(make_client):
    client = make_client()
    assert client.get("/batches/nope").status_code == 404
    assert client.post("/batches/nope/classify").status_code == 404
