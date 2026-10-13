"""Hidden acceptance tests for 03-csv-upload.

    python -m pytest _grader -q                          # grade your code (problem root)
    SOLUTION_DIR=_grader/reference python -m pytest _grader -q   # self-check the grader
    RUN_LIVE=1 OPENAI_API_KEY=sk-... python -m pytest _grader -q -m live   # real OpenAI

Fault tests (429 / 5xx / timeouts / bad output) point OPENAI_BASE_URL at a local
fake OpenAI server, because the real API cannot be made to fail on demand.
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

DATA = HERE / "data"
FAKE_KEY = "sk-test-SECRET-91f3c0ffee"
MIB = 1024 * 1024

# title marker -> scripted replies (see SPEC Part 2 retry rules); same as 01
OK = lambda c: ("json", {"category": c})  # noqa: E731
SCRIPT = {
    "Transcribe support call 1042": [OK("transcription")],
    "Label street scenes, batch 7": [OK("data_labeling")],
    "Evaluate summarizer v2": [OK("model_evaluation")],
    "Review flagged comments": [OK("content_moderation")],
    "Caption product photos": [("status", 429), OK("data_labeling")],
    "Grade chatbot answers": [("status", 500), ("status", 502), OK("model_evaluation")],
    "Moderate forum posts": [("text", "Sure! This one is content_moderation."), OK("content_moderation")],
    "Transcribe interview tape 3": [("sleep", 1.5, OK("transcription")), OK("transcription")],
    "Classify ticket 5531": [OK("HACKED")],
    "Benchmark reasoning model": [("status", 503)],
    "Audit label quality": [OK("spam")],
    "Review appeal 88": [OK("content_moderation")],
}
CATS = ["data_labeling", "model_evaluation", "content_moderation", "transcription", "other"]


def large_default(text):
    import re

    m = re.search(r"LRG-(\d{4})", text)
    return OK(CATS[int(m.group(1)) % 5] if m else "other")


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real OpenAI API (needs RUN_LIVE=1 and OPENAI_API_KEY)")


def pytest_collection_modifyitems(config, items):
    live_ok = os.environ.get("RUN_LIVE") == "1" and os.environ.get("OPENAI_API_KEY")
    for item in items:
        if "live" in item.keywords and not live_ok:
            item.add_marker(pytest.mark.skip(reason="set RUN_LIVE=1 and OPENAI_API_KEY to run live tests"))


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """An empty working directory: the app must not write anything into it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def llm(request, monkeypatch):
    if "live" in request.keywords:
        yield None
        return
    mock = MockLLM(FAKE_KEY, SCRIPT, default=large_default).start()
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OPENAI_BASE_URL", mock.url)
    monkeypatch.setenv("LLM_TIMEOUT", "0.5")
    monkeypatch.setenv("LLM_BACKOFF_BASE", "0.01")
    yield mock
    mock.stop()


@pytest.fixture
def client(workdir, llm):
    from fastapi.testclient import TestClient

    mod = importlib.import_module("app.main")
    with TestClient(mod.app) as c:
        yield c


def sample(name):
    return (DATA / name).read_bytes()


def upload(client, tasks=None, users=None, tasks_name="tasks.csv", users_name="users.csv", classify=None,
           omit=()):
    """POST /upload with multipart files. `tasks`/`users` are bytes (default: the sample files)."""
    files = {}
    if "tasks" not in omit:
        files["tasks"] = (tasks_name, sample("tasks.csv") if tasks is None else tasks, "text/csv")
    if "users" not in omit:
        files["users"] = (users_name, sample("users.csv") if users is None else users, "text/csv")
    params = {} if classify is None else {"classify": "true" if classify else "false"}
    return client.post("/upload", files=files, params=params)
