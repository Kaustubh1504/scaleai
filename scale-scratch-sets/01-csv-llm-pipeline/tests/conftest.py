import json
import shutil
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

PROBLEM = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROBLEM))

from app import main  # noqa: E402


class FakeLLM:
    """Scripted fake for POST /chat/completions.

    script: title -> list of replies, used one per call; the last reply repeats.
    A reply is an int (HTTP status), "timeout", or a string returned as the model's content.
    Anything not in the script answers {"category": "other"}.
    """

    def __init__(self, delay=0.0):
        self.script = {}
        self.calls = {}  # title -> number of calls
        self.in_flight = 0
        self.max_in_flight = 0
        self.delay = delay
        self.lock = threading.Lock()

    def total_calls(self):
        return sum(self.calls.values())

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        task = body["messages"][-1]["content"]
        title = json.loads(task.removeprefix("<task>").removesuffix("</task>"))["title"]

        with self.lock:
            n = self.calls.get(title, 0)
            self.calls[title] = n + 1
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                time.sleep(self.delay)
            replies = self.script.get(title, ['{"category": "other"}'])
            reply = replies[min(n, len(replies) - 1)]
            if reply == "timeout":
                raise httpx.ReadTimeout("fake timeout", request=request)
            if isinstance(reply, int):
                return httpx.Response(reply, json={"error": {"message": "fake"}})
            return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})
        finally:
            with self.lock:
                self.in_flight -= 1


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    shutil.copytree(PROBLEM / "data", tmp_path / "data")
    (tmp_path / "output").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BACKOFF_BASE", "0")
    monkeypatch.setattr(main, "make_http_client",
                        lambda: httpx.Client(transport=httpx.MockTransport(fake.handler)))
    return fake


@pytest.fixture
def client(workdir, llm):
    return TestClient(main.app)


def convert(client, tasks="data/tasks.csv", users="data/users.csv", output="output/tasks.json"):
    return client.post("/convert", json={"tasks_path": tasks, "users_path": users, "output_path": output})


def read_output(workdir, name="output/tasks.json"):
    return json.loads((workdir / name).read_text())
