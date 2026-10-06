"""Acceptance tests for prob-001.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.
"""

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(SOLUTION_DIR))

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from fastapi.testclient import TestClient  # noqa: E402

from mock_services.clock import FakeClock  # noqa: E402
from shared.mock_llm import KeywordClassifier, LLMConfig, MockLLMClient  # noqa: E402

# The keyword map is copied here so a candidate editing mock_services cannot change the expected labels.
KEYWORDS = {
    "billing": ["invoice", "charge", "charged", "refund", "payment", "billing", "subscription", "price"],
    "bug": ["error", "crash", "broken", "bug", "fail", "exception", "freeze"],
    "account_access": ["password", "login", "locked", "2fa", "sign in", "reset"],
    "feature_request": ["feature", "wish", "would love", "suggestion", "roadmap"],
}
EXPECTED_LABELS = {
    "T-1001": "billing", "T-1002": "bug", "T-1003": "account_access", "T-1004": "feature_request",
    "T-1005": "other", "T-1008": "billing", "T-1012": "billing", "T-1013": "account_access", "T-1015": "other",
}


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


def make_llm(config: LLMConfig | None = None, clock=None, responder=None) -> MockLLMClient:
    return MockLLMClient(config or LLMConfig(seed=11), responder=responder or KeywordClassifier(KEYWORDS, "other"),
                         clock=clock)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def make_client(tmp_path, clock):
    from app.main import create_app

    def build(llm=None, **kwargs) -> TestClient:
        return TestClient(create_app(storage_dir=tmp_path, llm=llm or make_llm(clock=clock), clock=clock, **kwargs))

    return build


def upload(client: TestClient, name: str = "tickets.csv", content: bytes | None = None):
    if content is None:
        content = (FIXTURES / name).read_bytes()
    return client.post("/uploads", files={"file": (name, content, "application/octet-stream")})


def upload_id_for(client: TestClient, name: str = "tickets.csv", content: bytes | None = None) -> str:
    resp = upload(client, name, content)
    assert resp.status_code == 201, resp.text
    return resp.json()["upload_id"]
