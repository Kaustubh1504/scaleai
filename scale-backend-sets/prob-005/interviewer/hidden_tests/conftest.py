"""Acceptance tests for prob-005.

Run against the candidate's code:
    SOLUTION_DIR=/path/to/candidate python -m pytest interviewer/hidden_tests
Skip the mid-part requirement change if you did not deliver it:
    ... -m "not change"
Without SOLUTION_DIR the tests run against interviewer/reference.
"""

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", HERE.parent / "reference")).resolve()
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(SOLUTION_DIR))

import httpx  # noqa: E402

import mock_services  # noqa: E402,F401  (puts shared/ on sys.path)
from shared.fake_clock import FakeClock  # noqa: E402
from shared.mock_webhook_receiver import WebhookReceiver  # noqa: E402

START = 1_700_000_000.0
# Copied here so candidate edits to data/ cannot change the outcome.
SUBSCRIPTIONS = json.loads((FIXTURES / "subscriptions.json").read_text())
AUDIT_KEYS = {"ts", "event_id", "subscription_id", "attempt", "outcome", "status_code", "error"}
DELIVERY_KEYS = {"event_id", "subscription_id", "status", "attempts", "next_attempt_at", "last_error"}


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


def pytest_configure(config):
    config.addinivalue_line("markers", "change: the mid-part requirement change (deselect with -m 'not change')")


def event(event_id: str, type: str = "task.completed", **data) -> dict:
    return {"id": event_id, "type": type, "created_at": "2024-06-01T10:00:00Z", "data": data or {"n": event_id}}


class Env:
    """Events file + subscriptions file + one mock receiver per subscription, all on one FakeClock.

    Every request goes through ``handler``: it is recorded in ``requests``, passed to
    ``before_send`` (which may raise to simulate a crash), then routed by URL path to
    that subscription's receiver.
    """

    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.clock = FakeClock(START)
        self.state_dir = tmp_path / "state"
        self.events_path = tmp_path / "events.jsonl"
        self.subs_path = tmp_path / "subscriptions.json"
        self.events_path.write_text("")
        self.requests: list[httpx.Request] = []
        self.before_send = None
        self.use_subscriptions(SUBSCRIPTIONS)

    def use_subscriptions(self, subs: list[dict]) -> None:
        self.subs_path.write_text(json.dumps(subs))
        self.secrets = {s["id"]: s["secret"] for s in subs}
        self.receivers = {s["id"]: WebhookReceiver(secret=s["secret"], clock=self.clock) for s in subs}

    def add(self, *items) -> None:
        """Append events (dicts) or raw lines (str) to the events file."""
        with self.events_path.open("a", encoding="utf-8") as fh:
            for item in items:
                fh.write((item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)) + "\n")

    def receiver(self, sub_id: str) -> WebhookReceiver:
        return self.receivers[sub_id]

    def client(self) -> httpx.Client:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if self.before_send is not None:
                self.before_send(request)
            return self.receivers[request.url.path.strip("/")].transport().handle_request(request)

        # A long default timeout, so a request that does not set its own is detectable.
        return httpx.Client(transport=httpx.MockTransport(handler), timeout=60)

    def dispatcher(self, **kwargs):
        from dispatcher.dispatcher import Dispatcher
        from dispatcher.events import EventStore
        from dispatcher.subscriptions import load_subscriptions

        return Dispatcher(self.state_dir, EventStore(self.events_path), load_subscriptions(self.subs_path),
                          self.client(), self.clock, **kwargs)

    def audit(self) -> list[dict]:
        path = self.state_dir / "audit.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []

    def sent(self, sub_id: str) -> list[str]:
        """Event ids of every request the subscription's receiver got, in order."""
        return [d.event_id for d in self.receivers[sub_id].deliveries]


@pytest.fixture
def env(tmp_path) -> Env:
    return Env(tmp_path)
