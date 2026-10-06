"""Acceptance tests for prob-010.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change (override reason) if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.
"""

import asyncio
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from fastapi.testclient import TestClient  # noqa: E402

from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_llm import KeywordClassifier, LLMConfig, MockLLMClient  # noqa: E402

T0 = 1_700_000_000.0

# Copied from candidate/mock_services/llm.py so candidate edits cannot change the expected labels.
KEYWORDS = {
    "contract": ["agreement", "contract", "party", "parties", "clause", "termination", "hereby", "signature"],
    "invoice": ["invoice", "amount due", "total due", "remit", "tax", "billed", "payment terms"],
    "id_document": ["passport", "driver license", "date of birth", "nationality", "identity", "id number"],
    "support_letter": ["complaint", "assistance", "help", "issue", "problem", "sincerely", "dear support"],
}

# (suffix, text, model label, pinned confidence, status with the default 0.8 threshold)
# Confidence is pinned by the "Ref D-00n" marker, so outcomes do not depend on how the
# candidate words the prompt, only on the document text being inside <item> tags.
DOCS = [
    ("001", "Services agreement between both parties, with a termination clause. Ref D-001", "contract", 0.95,
     "auto_accepted"),
    ("002", "Invoice 4410: amount due $120 including tax. Ref D-002", "invoice", 0.80, "auto_accepted"),
    ("003", "Passport scan. Nationality: Canadian. Ref D-003", "id_document", 0.79, "needs_review"),
    ("004", "Dear support, I need assistance with a billing problem. Ref D-004", "support_letter", 0.91,
     "auto_accepted"),
    ("005", "Quarterly newsletter about the office move. Ref D-005", "other", 0.40, "needs_review"),
    ("006", "Invoice attached to the agreement. Ref D-006", "contract", 0.60, "needs_review"),
]
PINNED = {f"Ref D-{suffix}": confidence for suffix, _, _, confidence, _ in DOCS}
MODEL_LABEL = {f"D-{suffix}": label for suffix, _, label, _, _ in DOCS}
EXPECTED_STATUS = {f"D-{suffix}": status for suffix, _, _, _, status in DOCS}
IDS = list(MODEL_LABEL)
REVIEW_IDS = [doc_id for doc_id, status in EXPECTED_STATUS.items() if status == "needs_review"]


class TriageResponder(KeywordClassifier):
    """The candidate's keyword classifier, with each test document's confidence pinned."""

    def classify(self, text: str) -> tuple[str, float]:
        label, confidence = super().classify(text)
        for marker, pinned in PINNED.items():
            if marker in text:
                return label, pinned
        return label, confidence


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


def make_llm(config: LLMConfig | None = None, clock=None, responder=None) -> MockLLMClient:
    return MockLLMClient(config or LLMConfig(seed=10), responder=responder or TriageResponder(KEYWORDS, "other"),
                         clock=clock)


@pytest.fixture
def clock():
    return FakeClock(start=T0)


@pytest.fixture
def make_client(tmp_path, clock):
    """Each call builds a new app over the same storage_dir (a restart)."""
    from app.main import create_app

    def build(llm=None, **kwargs) -> TestClient:
        return TestClient(create_app(storage_dir=tmp_path, llm=llm or make_llm(clock=clock), clock=clock, **kwargs))

    return build


def batch_content(prefix: str = "D", suffixes=None) -> bytes:
    lines = [json.dumps({"doc_id": f"{prefix}-{suffix}", "title": f"file-{suffix}.pdf", "text": text})
             for suffix, text, *_ in DOCS if suffixes is None or suffix in suffixes]
    return ("\n".join(lines) + "\n").encode()


def upload(client: TestClient, content: bytes | None = None, name: str = "docs.jsonl") -> str:
    resp = client.post("/batches", files={"file": (name, content or batch_content(), "application/octet-stream")})
    assert resp.status_code == 201, resp.text
    return resp.json()["batch_id"]


def classify(client: TestClient, batch_id: str) -> dict:
    resp = client.post(f"/batches/{batch_id}/classify")
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_doc(client: TestClient, doc_id: str) -> dict:
    resp = client.get(f"/documents/{doc_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def review(client: TestClient, doc_id: str, reviewer: str = "alice", label: str = "other", **extra):
    return client.post(f"/documents/{doc_id}/review", json={"reviewer": reviewer, "label": label, **extra})


def doc_audit(client: TestClient, doc_id: str) -> list[dict]:
    resp = client.get(f"/documents/{doc_id}/audit")
    assert resp.status_code == 200, resp.text
    return resp.json()["events"]


def all_audit(client: TestClient, **params) -> list[dict]:
    resp = client.get("/audit", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()["events"]


def run_at_once(fn, args_list):
    """Call fn(*args) from one thread per entry, released together by a barrier."""
    barrier = threading.Barrier(len(args_list))

    def call(args):
        barrier.wait()
        return fn(*args)

    with ThreadPoolExecutor(max_workers=len(args_list)) as pool:
        return list(pool.map(call, args_list))


class CountingLLM:
    """Wraps the mock; counts calls per test document marker. Optionally holds each call."""

    def __init__(self, inner, hold_s: float = 0.0):
        self.inner, self.hold_s = inner, hold_s
        self.lock = threading.Lock()
        self.prompts: list[str] = []

    def complete(self, prompt, **kwargs):
        with self.lock:
            self.prompts.append(prompt)
        time.sleep(self.hold_s)
        return self.inner.complete(prompt, **kwargs)

    async def acomplete(self, prompt, **kwargs):
        with self.lock:
            self.prompts.append(prompt)
        await asyncio.sleep(self.hold_s)
        return await self.inner.acomplete(prompt, **kwargs)

    def calls_for(self, doc_ref: str) -> int:
        with self.lock:
            return sum(f"Ref {doc_ref}" in p for p in self.prompts)

    @property
    def calls(self) -> int:
        with self.lock:
            return len(self.prompts)
