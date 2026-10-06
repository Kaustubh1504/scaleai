"""Starter test showing how to build the app with a fake LLM and clock.

Add your own tests next to this one.
"""

from fastapi.testclient import TestClient

from app.main import create_app
from mock_services.clock import FakeClock
from mock_services.llm import make_llm
from shared.mock_llm import LLMConfig


def test_health(tmp_path):
    clock = FakeClock()
    llm = make_llm(LLMConfig(seed=1), clock=clock)
    client = TestClient(create_app(storage_dir=tmp_path, llm=llm, clock=clock))
    assert client.get("/health").json() == {"status": "ok"}
