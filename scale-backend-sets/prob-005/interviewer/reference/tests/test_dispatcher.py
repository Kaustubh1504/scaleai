import json
import random

import httpx
import pytest

from dispatcher.dispatcher import Dispatcher, encode_body
from dispatcher.events import Event, EventStore
from dispatcher.state import StateError
from dispatcher.subscriptions import parse_subscriptions
from mock_services.clock import FakeClock
from mock_services.webhooks import WebhookReceiver

SUBS = [{"id": "sub_all", "url": "http://hooks.test/sub_all", "secret": "whsec_all", "event_types": ["*"]},
        {"id": "sub_tasks", "url": "http://hooks.test/sub_tasks", "secret": "whsec_tasks",
         "event_types": ["task.completed"]}]


class Harness:
    def __init__(self, tmp_path, subs=SUBS):
        self.clock = FakeClock()
        self.subs = parse_subscriptions(subs)
        self.receivers = {s.id: WebhookReceiver(secret=s.secret, clock=self.clock) for s in self.subs}
        self.events = EventStore(tmp_path / "events.jsonl")
        self.state_dir = tmp_path / "state"
        self.crash_on = None

    def transport(self):
        transports = {sid: r.transport() for sid, r in self.receivers.items()}

        def handler(request):
            if self.crash_on and request.headers["X-Event-Id"] == self.crash_on:
                raise RuntimeError("simulated crash")
            return transports[request.url.path.strip("/")].handle_request(request)

        return httpx.MockTransport(handler)

    def dispatcher(self, **kwargs):
        http = httpx.Client(transport=self.transport(), timeout=60)
        return Dispatcher(self.state_dir, self.events, self.subs, http, self.clock, rng=random.Random(1), **kwargs)

    def add(self, *ids, type="task.completed"):
        for event_id in ids:
            self.events.append(Event(event_id, type, "2024-06-01T00:00:00Z", {"n": event_id}))

    def audit(self):
        return [json.loads(line) for line in (self.state_dir / "audit.jsonl").read_text().splitlines()]


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def test_routes_signs_and_records(h):
    h.add("e1")
    h.add("e2", type="batch.exported")
    report = h.dispatcher().dispatch_due()
    assert (report.attempted, report.delivered, report.failed, report.dead) == (3, 3, 0, 0)
    assert h.receivers["sub_all"].accepted_event_ids() == ["e1", "e2"]
    assert h.receivers["sub_tasks"].accepted_event_ids() == ["e1"]
    delivery = h.receivers["sub_tasks"].deliveries[0]
    assert delivery.signature_valid and delivery.body == encode_body(h.events.read()[0])
    assert delivery.headers["content-type"] == "application/json"
    assert [(a["event_id"], a["subscription_id"], a["outcome"]) for a in h.audit()] == [
        ("e1", "sub_all", "delivered"), ("e1", "sub_tasks", "delivered"), ("e2", "sub_all", "delivered")]


def test_delivery_lookup(h):
    h.add("e1")
    d = h.dispatcher()
    d.dispatch_due()
    assert d.delivery("e1", "sub_all") == {"event_id": "e1", "subscription_id": "sub_all", "status": "delivered",
                                           "attempts": 1, "next_attempt_at": None, "last_error": None}
    with pytest.raises(KeyError):
        d.delivery("e1", "nope")


def test_retry_schedule_then_success(h):
    h.add("e1")
    h.receivers["sub_tasks"].script_event("e1", [503, "drop", 200])
    d = h.dispatcher()
    start = h.clock.time()
    d.dispatch_due()
    first = d.delivery("e1", "sub_tasks")
    assert first["status"] == "pending" and first["last_error"] == "HTTP 503"
    assert start + 5 <= first["next_attempt_at"] <= start + 10
    h.clock.set(first["next_attempt_at"] - 0.001)
    assert d.dispatch_due().attempted == 0
    h.clock.set(first["next_attempt_at"])
    d.dispatch_due()
    second = d.delivery("e1", "sub_tasks")
    assert second["last_error"].startswith("ConnectError")
    assert h.clock.time() + 10 <= second["next_attempt_at"] <= h.clock.time() + 20
    h.clock.set(second["next_attempt_at"])
    assert d.dispatch_due().delivered == 1
    assert [a["outcome"] for a in h.audit() if a["subscription_id"] == "sub_tasks"] == ["failed", "failed", "delivered"]


def test_retry_after_and_at_most_once_per_call(h):
    h.add("e1")
    h.receivers["sub_tasks"].script_event("e1", ["429:0", "429:900"])
    d = h.dispatcher()
    assert d.dispatch_due().attempted == 2  # sub_all + one attempt for sub_tasks, though it is due again at once
    assert d.delivery("e1", "sub_tasks")["next_attempt_at"] == h.clock.time()
    d.dispatch_due()
    assert d.delivery("e1", "sub_tasks")["next_attempt_at"] == h.clock.time() + 900


@pytest.mark.parametrize("script, max_attempts, outcomes", [
    ([404], 5, ["dead"]),
    ([500, 500, 500], 3, ["failed", "failed", "dead"]),
    (["timeout", "timeout"], 2, ["failed", "dead"]),
])
def test_dead_lettering(h, script, max_attempts, outcomes):
    h.add("e1")
    h.receivers["sub_tasks"].script_event("e1", script)
    d = h.dispatcher(max_attempts=max_attempts)
    for _ in range(len(script) + 2):
        d.dispatch_due()
        h.clock.advance(1000)
    assert d.delivery("e1", "sub_tasks")["status"] == "dead"
    assert d.delivery("e1", "sub_tasks")["next_attempt_at"] is None
    assert [a["outcome"] for a in h.audit() if a["subscription_id"] == "sub_tasks"] == outcomes
    assert len(h.receivers["sub_tasks"].attempts_for("e1")) == len(outcomes)


def test_every_request_has_the_timeout(h, monkeypatch):
    seen = []
    h.add("e1")
    d = h.dispatcher()
    original = d.http.post
    monkeypatch.setattr(d.http, "post", lambda *a, **kw: seen.append(kw["timeout"]) or original(*a, **kw))
    d.dispatch_due()
    assert seen == [5.0, 5.0]


def test_restart_resumes_exactly(h):
    h.add("e1", "e2")
    h.receivers["sub_tasks"].script_event("e2", [503])
    h.receivers["sub_all"].script_event("e2", [410])
    first = h.dispatcher()
    first.dispatch_due()
    snapshot = {k: first.delivery(*k) for k in [("e1", "sub_all"), ("e2", "sub_tasks"), ("e2", "sub_all")]}

    second = h.dispatcher()
    assert {k: second.delivery(*k) for k in snapshot} == snapshot
    assert second.dispatch_due().attempted == 0
    h.add("e3")
    h.clock.set(snapshot[("e2", "sub_tasks")]["next_attempt_at"])
    report = h.dispatcher().dispatch_due()
    assert (report.attempted, report.delivered) == (3, 3)  # e2->tasks retry, e3 x2; e2->all stays dead
    assert sorted(h.receivers["sub_all"].accepted_event_ids()) == ["e1", "e3"]
    assert len(h.audit()) == 7


def test_crash_propagates_and_earlier_attempts_stay_saved(h):
    h.add("e1", "e2", "e3")
    h.crash_on = "e2"
    with pytest.raises(RuntimeError):
        h.dispatcher().dispatch_due()
    h.crash_on = None
    h.dispatcher().dispatch_due()
    for receiver in h.receivers.values():
        assert receiver.accepted_event_ids() == ["e1", "e2", "e3"]


def test_corrupt_state_is_refused(h):
    h.state_dir.mkdir()
    (h.state_dir / "deliveries.json").write_text("{trunc")
    with pytest.raises(StateError):
        h.dispatcher()


def test_bad_max_attempts(h):
    with pytest.raises(ValueError):
        h.dispatcher(max_attempts=0)
