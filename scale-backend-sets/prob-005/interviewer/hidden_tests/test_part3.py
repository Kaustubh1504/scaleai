"""Part 3: durable state, restart/resume, idempotent re-runs, crash safety (at-least-once)."""

import json
import os
import subprocess
import sys

import pytest

from conftest import SOLUTION_DIR, event

ONE_SUB = [{"id": "sub_x", "url": "http://hooks.test/sub_x", "secret": "whsec_x", "event_types": ["*"]}]


@pytest.fixture
def one(env):
    env.use_subscriptions(ONE_SUB)
    return env


def test_restart_never_resends_delivered(env):
    env.add(event("e1"), event("e2", "batch.exported"))
    env.dispatcher().dispatch_due()
    env.clock.advance(3600)
    report = env.dispatcher().dispatch_due()
    assert report.attempted == 0
    assert env.sent("sub_all") == ["e1", "e2"] and env.sent("sub_tasks") == ["e1"]


def test_new_instance_reports_saved_state_before_dispatching(env):
    env.add(event("e1"), event("e2"))
    env.receiver("sub_tasks").script_event("e1", [503])
    env.receiver("sub_tasks").script_event("e2", [404])
    first = env.dispatcher()
    first.dispatch_due()
    keys = [("e1", "sub_all"), ("e1", "sub_tasks"), ("e2", "sub_all"), ("e2", "sub_tasks")]
    before = {k: first.delivery(*k) for k in keys}
    assert [before[k]["status"] for k in keys] == ["delivered", "pending", "delivered", "dead"]
    second = env.dispatcher()
    assert {k: second.delivery(*k) for k in keys} == before


def test_pending_schedule_resumes_exactly(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [500])
    first = one.dispatcher()
    first.dispatch_due()
    due = first.delivery("e1", "sub_x")["next_attempt_at"]

    one.clock.set(due - 0.01)
    second = one.dispatcher()
    assert second.dispatch_due().attempted == 0
    one.clock.set(due)
    third = one.dispatcher()
    report = third.dispatch_due()
    assert (report.attempted, report.delivered) == (1, 1)
    d = third.delivery("e1", "sub_x")
    assert (d["status"], d["attempts"]) == ("delivered", 2)
    assert len(one.receiver("sub_x").attempts_for("e1")) == 2


def test_attempt_count_survives_restart_for_dead_lettering(one):
    one.add(event("e1"))
    one.receiver("sub_x").fail_always(500)
    for _ in range(6):  # a fresh process every pass
        one.dispatcher(max_attempts=3).dispatch_due()
        one.clock.advance(1000)
    assert len(one.receiver("sub_x").attempts_for("e1")) == 3
    assert one.dispatcher(max_attempts=3).delivery("e1", "sub_x")["status"] == "dead"


def test_dead_stays_dead_after_restart(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [410])
    one.dispatcher().dispatch_due()
    one.clock.advance(3600)
    restarted = one.dispatcher()
    assert restarted.delivery("e1", "sub_x")["status"] == "dead"
    assert restarted.dispatch_due().attempted == 0
    assert len(one.receiver("sub_x").deliveries) == 1


def test_rerun_at_same_time_sends_nothing_new(env):
    env.add(event("e1"), event("e2"))
    env.receiver("sub_all").script_event("e2", [503])
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    sent = len(env.requests)
    assert dispatcher.dispatch_due().attempted == 0
    assert env.dispatcher().dispatch_due().attempted == 0
    assert len(env.requests) == sent


def test_events_appended_between_runs_are_delivered(env):
    env.add(event("e1"))
    env.dispatcher().dispatch_due()
    env.add(event("e2"), event("e3", "batch.exported"))
    report = env.dispatcher().dispatch_due()
    assert (report.attempted, report.delivered) == (3, 3)
    assert env.sent("sub_all") == ["e1", "e2", "e3"] and env.sent("sub_tasks") == ["e1", "e2"]


def test_audit_log_is_appended_across_restarts(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [500])
    first = one.dispatcher()
    first.dispatch_due()
    one.clock.set(first.delivery("e1", "sub_x")["next_attempt_at"])
    one.add(event("e2"))
    one.dispatcher().dispatch_due()
    assert [(a["event_id"], a["attempt"], a["outcome"]) for a in one.audit()] == [
        ("e1", 1, "failed"), ("e1", 2, "delivered"), ("e2", 1, "delivered")]


def test_crash_propagates_and_completed_attempts_stay_saved(env):
    env.add(*[event(f"e{i}") for i in range(1, 5)])
    count = {"n": 0}

    def crash_on_fourth(request):
        count["n"] += 1
        if count["n"] == 4:
            raise RuntimeError("simulated crash")

    env.before_send = crash_on_fourth
    with pytest.raises(RuntimeError):
        env.dispatcher().dispatch_due()
    assert env.sent("sub_all") == ["e1", "e2"] and env.sent("sub_tasks") == ["e1"]

    env.before_send = None
    restarted = env.dispatcher()  # the saved state must still load
    restarted.dispatch_due()
    # the crash happened before the 4th request was sent, so nothing is duplicated
    assert env.sent("sub_all") == ["e1", "e2", "e3", "e4"]
    assert env.sent("sub_tasks") == ["e1", "e2", "e3", "e4"]
    assert all(restarted.delivery(f"e{i}", s)["status"] == "delivered"
               for i in range(1, 5) for s in ("sub_all", "sub_tasks"))


CHILD = r"""
import json, os, sys
from pathlib import Path

import httpx
import mock_services  # noqa: F401
from shared.fake_clock import FakeClock
from dispatcher.dispatcher import Dispatcher
from dispatcher.events import EventStore
from dispatcher.subscriptions import load_subscriptions

state_dir, events_path, subs_path, log_path, kill_at, start = sys.argv[1:7]
count = 0


def handler(request):
    global count
    count += 1
    with open(log_path, "a") as fh:
        fh.write(json.dumps({"n": count, "event_id": request.headers.get("X-Event-Id")}) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    if count == int(kill_at):
        os._exit(17)  # killed after the subscriber got the request, before the result is saved
    return httpx.Response(200, json={"received": True})


http = httpx.Client(transport=httpx.MockTransport(handler))
Dispatcher(Path(state_dir), EventStore(Path(events_path)), load_subscriptions(Path(subs_path)), http,
           FakeClock(float(start))).dispatch_due()
os._exit(0)
"""


def test_killed_between_send_and_save_is_at_least_once(one, tmp_path):
    one.add(*[event(f"e{i}") for i in range(1, 6)])
    log_path = tmp_path / "child_requests.jsonl"
    env_vars = {**os.environ, "PYTHONPATH": os.pathsep.join([str(SOLUTION_DIR), os.environ.get("PYTHONPATH", "")])}
    proc = subprocess.run(
        [sys.executable, "-c", CHILD, str(one.state_dir), str(one.events_path), str(one.subs_path), str(log_path),
         "3", repr(one.clock.time())],
        cwd=SOLUTION_DIR, env=env_vars, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 17, proc.stderr[-2000:]
    child_sent = [json.loads(line)["event_id"] for line in log_path.read_text().splitlines()]
    assert child_sent == ["e1", "e2", "e3"]

    restarted = one.dispatcher()  # state written by the killed process must load
    restarted.dispatch_due()
    # e1, e2 were acknowledged and saved: never again. e3's result was never saved: sent again. e4, e5: new.
    assert one.receiver("sub_x").accepted_event_ids() == ["e3", "e4", "e5"]
    assert all(restarted.delivery(f"e{i}", "sub_x")["status"] == "delivered" for i in range(1, 6))
