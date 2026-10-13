"""Hidden acceptance tests for 04-llm-triage.

    python -m pytest _grader -q                          # grade your code (problem root)
    SOLUTION_DIR=_grader/reference python -m pytest _grader -q   # self-check the grader
    RUN_LIVE=1 OPENAI_API_KEY=sk-... python -m pytest _grader -q -m live   # real OpenAI

Fault tests (429 / 5xx / timeouts / bad output) point OPENAI_BASE_URL at a local
fake OpenAI server, because the real API cannot be made to fail on demand.
Every scripted ticket carries a unique marker like "[ticket-07]" that the fake keys on.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PROBLEM = HERE.parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", PROBLEM)).resolve()
sys.path.insert(0, str(SOLUTION_DIR))
sys.path.insert(0, str(PROBLEM.parent / "_grader_shared"))

from mock_llm import MockLLM  # noqa: E402

FAKE_KEY = "sk-test-SECRET-4a7e1dbeef"

GOOD = {"category": "bug", "urgency": 4, "summary": "Export button crashes the app."}
J = lambda obj: ("json", obj)  # noqa: E731
T = lambda s: ("text", s)  # noqa: E731
OK = J(GOOD)
GOOD_TEXT = '{"category": "bug", "urgency": 4, "summary": "Export button crashes the app."}'


def bad(**kw):
    return {**GOOD, **kw}


SCRIPT = {
    # ---- Part 1: parsing
    "[ticket-01]": [OK],                                                   # clean JSON
    "[ticket-02]": [T("```json\n" + GOOD_TEXT + "\n```")],                 # ```json fence
    "[ticket-03]": [T("```\n" + GOOD_TEXT + "\n```")],                     # bare ``` fence
    "[ticket-04]": [T("  \n\n" + GOOD_TEXT + "\n  \n")],                   # surrounding whitespace
    "[ticket-05]": [J({**GOOD, "confidence": 0.9, "note": "RAW-MODEL-NOTE"})],  # extra keys
    "[ticket-06]": [J(bad(urgency="3")), OK],                              # string urgency, then ok
    "[ticket-07]": [J(bad(summary="  Export button crashes the app.  "))],  # summary is stripped
    "[ticket-08]": [J({"category": "billing", "urgency": 1, "summary": "x" * 200})],  # boundary ok
    "[ticket-09]": [J({"category": "feature_request", "urgency": 5, "summary": "Wants dark mode."})],
    # ---- invalid twice -> 502 llm_bad_response, exactly 2 calls
    "[ticket-20]": [J(bad(urgency=9))],
    "[ticket-21]": [J(bad(urgency=0))],
    "[ticket-22]": [J(bad(urgency=True))],
    "[ticket-23]": [J(bad(urgency="3"))],
    "[ticket-24]": [J(bad(urgency=3.0))],
    "[ticket-25]": [J(bad(category="HACKED"))],
    "[ticket-26]": [J(bad(category="Billing"))],
    "[ticket-27]": [J(bad(summary="y" * 250))],
    "[ticket-28]": [J(bad(summary="   "))],
    "[ticket-29]": [J(bad(summary=42))],
    "[ticket-30]": [J({"category": "bug", "urgency": 2})],                 # missing summary
    "[ticket-31]": [J([GOOD])],                                            # not an object
    "[ticket-32]": [T("Sure! Category: bug, urgency 4.")],                 # not JSON
    "[ticket-33]": [T("```json\n{\"category\": \"bug\", \"urgency\": 4,\n```")],  # truncated
    "[ticket-34]": [T("")],                                                # empty reply
    # injection: the fake "falls for it" every time
    "[ticket-35]": [J({"category": "HACKED", "urgency": 5, "summary": "pwned"})],
    "[ticket-36]": [J(bad(category="HACKED")), OK],                         # fooled once, then ok
    # ---- Part 2: transport
    "[ticket-40]": [("status", 429), OK],                                  # 2 calls, 200
    "[ticket-41]": [("status", 500)],                                      # 3 calls, 503
    "[ticket-42]": [("status", 502), ("status", 503), OK],                 # 3 calls, 200
    "[ticket-43]": [("sleep", 1.5, OK), OK],                               # timeout: 1 call, 504
    "[ticket-44]": [("status", 401), OK],                                  # 1 call, 502 llm_error
    "[ticket-45]": [("status", 400), OK],                                  # 1 call, 502 llm_error
    "[ticket-46]": [("status", 429), ("status", 429), ("status", 429), OK],  # 3 calls, 503
    "[ticket-47]": [T("nope"), ("status", 429), OK],                       # 3 calls, 200
    "[ticket-48]": [T("nope"), ("status", 500)],                           # 1 + 3 calls, 503
    "[ticket-49]": [T("nope"), ("sleep", 1.5, OK), OK],                    # 2 calls, 504
    "[ticket-50]": [("status", 503)],                                      # backoff timing
    "[ticket-51]": [("status", 403), OK],                                  # 1 call, 502 llm_error
}


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real OpenAI API (needs RUN_LIVE=1 and OPENAI_API_KEY)")


def pytest_collection_modifyitems(config, items):
    live_ok = os.environ.get("RUN_LIVE") == "1" and os.environ.get("OPENAI_API_KEY")
    for item in items:
        if "live" in item.keywords and not live_ok:
            item.add_marker(pytest.mark.skip(reason="set RUN_LIVE=1 and OPENAI_API_KEY to run live tests"))


@pytest.fixture(scope="session")
def _mock():
    # one server for the whole run: MockLLM.stop() blocks ~0.5 s (serve_forever poll interval)
    mock = MockLLM(FAKE_KEY, SCRIPT, default=lambda text: OK).start()
    yield mock
    mock.stop()


@pytest.fixture
def llm(request, monkeypatch, _mock):
    if "live" in request.keywords:
        yield None
        return
    mock = _mock
    mock.set_script(SCRIPT)
    mock.reset_counts()
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OPENAI_BASE_URL", mock.url)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("LLM_TIMEOUT", "0.5")
    monkeypatch.setenv("LLM_BACKOFF_BASE", "0.01")
    yield mock


@pytest.fixture
def client(llm):
    from fastapi.testclient import TestClient

    mod = importlib.import_module("app.main")
    with TestClient(mod.app) as c:
        yield c


def ticket(marker: str, body: str = "The export button crashes the app every time.") -> str:
    return f"{marker} {body}"


def triage(client, text):
    return client.post("/triage", json={"text": text})
