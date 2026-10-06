"""Part 1: routing, request shape and signature, delivered-once, audit log, skipped lines."""

import json

import pytest

from conftest import AUDIT_KEYS, DELIVERY_KEYS, START, event

# Part 2 schedules retries 5-10 s after a first failure; Part 1 tests that expect a
# retry move the clock well past that so they hold for any finished solution.
LATER = 600


def test_routes_each_event_to_matching_subscriptions_in_order(env):
    env.add(event("e1", "task.completed"), event("e2", "batch.exported"), event("e3", "task.failed"),
            event("e4", "user.deleted"))
    report = env.dispatcher().dispatch_due()
    assert env.receiver("sub_all").accepted_event_ids() == ["e1", "e2", "e3", "e4"]
    assert env.receiver("sub_tasks").accepted_event_ids() == ["e1", "e3"]
    assert (report.attempted, report.delivered, report.failed, report.dead) == (6, 6, 0, 0)
    assert report.skipped_lines == []


def test_request_body_headers_and_signature(env):
    evt = event("e1", "task.completed", task_id="t_1", note="café ☕", nested={"a": [1, 2]})
    env.add(evt)
    env.dispatcher().dispatch_due()
    assert len(env.requests) == 2
    for sub_id in ("sub_all", "sub_tasks"):
        (got,) = env.receiver(sub_id).deliveries
        assert got.method == "POST"
        assert got.json == evt
        headers = {k.lower(): v for k, v in got.headers.items()}
        assert headers["content-type"].split(";")[0].strip() == "application/json"
        assert headers["x-event-id"] == "e1"
        assert got.signature_valid is True, f"signature for {sub_id} does not verify"
        assert headers["x-webhook-signature"].startswith(f"t={int(START)},")


def test_delivered_is_never_sent_again(env):
    env.add(event("e1"), event("e2"))
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    env.clock.advance(LATER)
    report = dispatcher.dispatch_due()
    assert report.attempted == 0
    assert env.sent("sub_all") == ["e1", "e2"] and env.sent("sub_tasks") == ["e1", "e2"]


def test_delivery_state_after_success(env):
    env.add(event("e1"))
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    d = dispatcher.delivery("e1", "sub_tasks")
    assert set(d) == DELIVERY_KEYS
    assert d == {"event_id": "e1", "subscription_id": "sub_tasks", "status": "delivered", "attempts": 1,
                 "next_attempt_at": None, "last_error": None}


def test_unknown_delivery_raises_key_error(env):
    env.add(event("e1", "batch.exported"))
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    with pytest.raises(KeyError):
        dispatcher.delivery("e1", "sub_tasks")  # sub_tasks does not want batch.exported
    with pytest.raises(KeyError):
        dispatcher.delivery("nope", "sub_all")


def test_failed_attempt_stays_pending_and_is_retried(env):
    env.add(event("e1"), event("e2"))
    env.receiver("sub_tasks").script_event("e1", [503])
    dispatcher = env.dispatcher()
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.delivered, report.failed) == (4, 3, 1)
    d = dispatcher.delivery("e1", "sub_tasks")
    assert (d["status"], d["attempts"]) == ("pending", 1)
    assert isinstance(d["last_error"], str) and "503" in d["last_error"]
    assert isinstance(d["next_attempt_at"], float | int)
    # the failure did not stop later deliveries
    assert env.receiver("sub_tasks").accepted_event_ids() == ["e2"]

    env.clock.advance(LATER)
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.delivered, report.failed) == (1, 1, 0)
    d = dispatcher.delivery("e1", "sub_tasks")
    assert (d["status"], d["attempts"], d["next_attempt_at"], d["last_error"]) == ("delivered", 2, None, None)
    assert env.sent("sub_tasks") == ["e1", "e2", "e1"]
    assert env.sent("sub_all") == ["e1", "e2"]


def test_connection_error_is_a_failed_attempt(env):
    env.add(event("e1"))
    env.receiver("sub_tasks").script_event("e1", ["drop"])
    dispatcher = env.dispatcher()
    report = dispatcher.dispatch_due()  # must not raise
    assert (report.attempted, report.delivered, report.failed) == (2, 1, 1)
    d = dispatcher.delivery("e1", "sub_tasks")
    assert d["status"] == "pending" and "ConnectError" in d["last_error"]
    env.clock.advance(LATER)
    dispatcher.dispatch_due()
    assert dispatcher.delivery("e1", "sub_tasks")["status"] == "delivered"


def test_audit_log_records_every_attempt(env):
    env.add(event("e1"))
    env.receiver("sub_tasks").script_event("e1", [500, "drop"])
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    env.clock.advance(LATER)
    dispatcher.dispatch_due()
    env.clock.advance(LATER)
    dispatcher.dispatch_due()

    lines = env.audit()
    assert all(set(line) == AUDIT_KEYS for line in lines)
    assert [(a["event_id"], a["subscription_id"], a["attempt"], a["outcome"], a["status_code"]) for a in lines] == [
        ("e1", "sub_all", 1, "delivered", 200),
        ("e1", "sub_tasks", 1, "failed", 500),
        ("e1", "sub_tasks", 2, "failed", None),
        ("e1", "sub_tasks", 3, "delivered", 200),
    ]
    assert [a["ts"] for a in lines] == [START, START, START + LATER, START + 2 * LATER]
    assert lines[0]["error"] is None and lines[3]["error"] is None
    assert "500" in lines[1]["error"] and "ConnectError" in lines[2]["error"]


def test_bad_lines_are_skipped_and_reported(env):
    env.add(
        event("e1"),                                                  # 1
        '{"id": "e2", "type": "task.completed", "created_at"',       # 2 truncated JSON
        "",                                                           # 3 blank: ignored, not reported
        '["e3", "task.completed"]',                                   # 4 not an object
        {"id": "e4", "type": "task.completed", "created_at": "x"},    # 5 no data
        {"id": "", "type": "task.completed", "created_at": "x", "data": {}},  # 6 empty id
        event("e5", "batch.exported"),                                # 7
        event("e1", "batch.exported"),                                # 8 duplicate id
        "   ",                                                        # 9 whitespace only
        event("e6"),                                                  # 10
    )
    dispatcher = env.dispatcher()
    report = dispatcher.dispatch_due()
    assert report.skipped_lines == [2, 4, 5, 6, 8]
    assert env.receiver("sub_all").accepted_event_ids() == ["e1", "e5", "e6"]
    assert env.receiver("sub_tasks").accepted_event_ids() == ["e1", "e6"]
    assert env.receiver("sub_all").attempts_for("e1")[0].json["type"] == "task.completed"  # first occurrence wins
    assert report.attempted == 5
    # skipped lines are reported again on later calls
    assert dispatcher.dispatch_due().skipped_lines == [2, 4, 5, 6, 8]


def test_events_appended_later_are_picked_up(env):
    env.add(event("e1"))
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    env.add(event("e2", "batch.exported"))
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.delivered) == (1, 1)
    assert env.sent("sub_all") == ["e1", "e2"] and env.sent("sub_tasks") == ["e1"]


def test_audit_file_lives_in_state_dir_and_is_json_lines(env):
    env.add(event("e1"))
    env.dispatcher().dispatch_due()
    raw = (env.state_dir / "audit.jsonl").read_text()
    assert raw.endswith("\n") and len(raw.splitlines()) == 2
    assert all(json.loads(line)["outcome"] == "delivered" for line in raw.splitlines())
