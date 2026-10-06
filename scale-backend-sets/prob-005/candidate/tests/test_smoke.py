"""Starter tests: how to build a Dispatcher with the mock receiver and a fake clock.

Add your own tests next to these.
"""

import json
from pathlib import Path

import httpx
import pytest

from dispatcher.dispatcher import Dispatcher
from dispatcher.events import Event, EventStore
from dispatcher.subscriptions import SubscriptionError, load_subscriptions, parse_subscriptions
from mock_services.clock import FakeClock
from mock_services.webhooks import WebhookReceiver

DATA = Path(__file__).resolve().parent.parent / "data"


def test_event_store_reads_sample_and_skips_malformed_lines():
    events = EventStore(DATA / "events.jsonl").read()
    assert [e.id for e in events][:2] == ["evt_0001", "evt_0002"]
    assert all(e.id and e.type and isinstance(e.data, dict) for e in events)


def test_event_store_append_round_trip(tmp_path):
    store = EventStore(tmp_path / "events.jsonl")
    assert store.read() == []
    store.append(Event("evt_1", "task.completed", "2024-06-01T00:00:00Z", {"task_id": "t_1"}))
    assert store.read() == [Event("evt_1", "task.completed", "2024-06-01T00:00:00Z", {"task_id": "t_1"})]


def test_sample_subscriptions_load():
    subs = {s.id: s for s in load_subscriptions(DATA / "subscriptions.json")}
    assert subs["sub_warehouse"].wants("anything.at.all")
    assert subs["sub_exports"].wants("batch.exported") and not subs["sub_exports"].wants("task.completed")


@pytest.mark.parametrize("raw", [
    {"id": "s"},
    [{"id": "s", "url": "ftp://x", "secret": "k", "event_types": ["*"]}],
    [{"id": "s", "url": "http://x", "secret": "", "event_types": ["*"]}],
    [{"id": "s", "url": "http://x", "secret": "k", "event_types": []}],
    [{"id": "s", "url": "http://x", "secret": "k", "event_types": ["*"]}] * 2,
])
def test_invalid_subscriptions_are_rejected(raw):
    with pytest.raises(SubscriptionError):
        parse_subscriptions(raw)


def test_dispatch_posts_to_matching_subscribers(tmp_path):
    clock = FakeClock()
    receiver = WebhookReceiver(clock=clock)
    events = EventStore(tmp_path / "events.jsonl")
    events.append(Event("evt_1", "task.completed", "2024-06-01T00:00:00Z", {}))
    events.append(Event("evt_2", "batch.exported", "2024-06-01T00:00:00Z", {}))
    subs = parse_subscriptions([{"id": "sub_tasks", "url": "http://hooks.test/tasks", "secret": "whsec",
                                 "event_types": ["task.completed"]}])
    dispatcher = Dispatcher(tmp_path / "state", events, subs, httpx.Client(transport=receiver.transport()), clock)

    dispatcher.dispatch_due()

    assert receiver.accepted_event_ids() == ["evt_1"]
    assert json.loads(receiver.deliveries[0].body)["type"] == "task.completed"
