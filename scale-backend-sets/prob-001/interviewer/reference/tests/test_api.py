import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import LLMConfig

DATA = Path(__file__).resolve().parents[3] / "candidate" / "data"


@pytest.fixture
def make_client(tmp_path):
    def build(config: LLMConfig | None = None, llm=None, **kwargs):
        clock = FakeClock()
        llm = llm or make_llm(config or LLMConfig(seed=3), clock)
        return TestClient(create_app(storage_dir=tmp_path, llm=llm, clock=clock, **kwargs))

    return build


def upload(client, name="tickets.csv", content=None):
    content = (DATA / name).read_bytes() if content is None else content
    return client.post("/uploads", files={"file": (name, content, "text/csv")})


def test_upload_sample_and_read_back(make_client, tmp_path):
    client = make_client()
    resp = upload(client)
    assert resp.status_code == 201
    body = resp.json()
    assert (body["total_rows"], body["valid_rows"], body["invalid_rows"]) == (18, 9, 9)
    assert [(e["row"], e["field"]) for e in body["errors"]] == [
        (6, "customer_email"), (7, "subject"), (9, "ticket_id"), (10, "created_at"), (11, None),
        (12, None), (13, "ticket_id"), (16, "created_at"), (18, "body")]
    saved = json.loads((tmp_path / "uploads" / f"{body['upload_id']}.json").read_text())
    assert client.get(f"/uploads/{body['upload_id']}").json() == saved
    assert len(saved["tickets"]) == 9


@pytest.mark.parametrize("name, content, status", [
    ("tickets.txt", b"x", 415),
    ("tickets.csv", b"", 400),
    ("tickets_bad_header.csv", None, 400),
    ("tickets.csv", b"\xff\xfe", 400),
])
def test_upload_rejections(make_client, name, content, status):
    assert upload(make_client(), name, content).status_code == status


def test_missing_file_field(make_client):
    assert make_client().post("/uploads").status_code == 422


def test_unknown_and_malicious_ids(make_client):
    client = make_client()
    for upload_id in ("0" * 32, "..%2F..%2Fetc", "nope"):
        assert client.get(f"/uploads/{upload_id}").status_code == 404
        assert client.post(f"/uploads/{upload_id}/classify").status_code == 404


def test_classify_and_persist(make_client, tmp_path):
    client = make_client()
    upload_id = upload(client).json()["upload_id"]
    assert client.get(f"/uploads/{upload_id}/classifications").status_code == 404
    body = client.post(f"/uploads/{upload_id}/classify").json()
    labels = {r["ticket_id"]: r["label"] for r in body["results"]}
    assert labels == {"T-1001": "billing", "T-1002": "bug", "T-1003": "account_access", "T-1004": "feature_request",
                      "T-1005": "other", "T-1008": "billing", "T-1012": "billing", "T-1013": "account_access",
                      "T-1015": "other"}
    assert body["classified"] == 9 and body["failed"] == 0
    assert client.get(f"/uploads/{upload_id}/classifications").json() == body
    assert json.loads((tmp_path / "classifications" / f"{upload_id}.json").read_text()) == body


def test_rerun_only_retries_failures(make_client):
    llm = make_llm(LLMConfig(prompt_faults={"dark mode": ["malformed"] * 3}), FakeClock())
    client = make_client(llm=llm)
    upload_id = upload(client).json()["upload_id"]
    first = client.post(f"/uploads/{upload_id}/classify").json()
    assert first["failed"] == 1
    calls_before = llm.usage.calls + llm.usage.failed_calls
    second = client.post(f"/uploads/{upload_id}/classify").json()
    assert llm.usage.calls + llm.usage.failed_calls - calls_before == 1
    assert second["classified"] == 9 and second["failed"] == 0


class CountingLLM:
    def __init__(self, inner):
        self.inner, self.lock, self.active, self.peak = inner, threading.Lock(), 0, 0

    def complete(self, prompt, **kwargs):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(0.02)
            return self.inner.complete(prompt, **kwargs)
        finally:
            with self.lock:
                self.active -= 1


def test_concurrency_is_bounded(make_client):
    llm = CountingLLM(make_llm(LLMConfig(), FakeClock()))
    client = make_client(llm=llm, max_concurrency=3)
    upload_id = upload(client, "tickets_2k.csv", (DATA / "tickets_2k.csv").read_bytes()[:8000]).json()["upload_id"]
    body = client.post(f"/uploads/{upload_id}/classify").json()
    assert body["classified"] > 30
    assert 2 <= llm.peak <= 3
