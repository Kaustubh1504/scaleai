"""Part 2: scheduled retries, backoff with jitter, Retry-After, dead-lettering.

Tests marked ``change`` cover the mid-part requirement change (5 s timeout,
timeouts retryable). The others never script a timeout.
"""

import pytest

from conftest import event

ONE_SUB = [{"id": "sub_x", "url": "http://hooks.test/sub_x", "secret": "whsec_x", "event_types": ["*"]}]
TWO_SUBS = ONE_SUB + [{"id": "sub_y", "url": "http://hooks.test/sub_y", "secret": "whsec_y", "event_types": ["*"]}]


@pytest.fixture
def one(env):
    env.use_subscriptions(ONE_SUB)
    return env


def attempt_until_settled(env, dispatcher, rounds=12):
    for _ in range(rounds):
        dispatcher.dispatch_due()
        env.clock.advance(1000)


def test_exponential_backoff_schedule(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [500, 502, 503, 500, 200])
    dispatcher = one.dispatcher()
    for n, ceiling in enumerate([10, 20, 40, 80], start=1):
        t = one.clock.time()
        report = dispatcher.dispatch_due()
        assert (report.attempted, report.failed) == (1, 1)
        d = dispatcher.delivery("e1", "sub_x")
        assert (d["status"], d["attempts"]) == ("pending", n)
        delay = d["next_attempt_at"] - t
        assert ceiling / 2 <= delay <= ceiling, f"attempt {n}: delay {delay}"
        one.clock.set(d["next_attempt_at"])  # due exactly at next_attempt_at
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.delivered) == (1, 1)
    assert dispatcher.delivery("e1", "sub_x")["status"] == "delivered"


def test_backoff_is_capped_at_300(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [500] * 8)
    dispatcher = one.dispatcher(max_attempts=10)
    delays = []
    for _ in range(8):
        t = one.clock.time()
        dispatcher.dispatch_due()
        d = dispatcher.delivery("e1", "sub_x")
        delays.append(d["next_attempt_at"] - t)
        one.clock.set(d["next_attempt_at"])
    assert 80 <= delays[4] <= 160
    assert all(150 <= x <= 300 for x in delays[5:]), delays


def test_not_attempted_before_due(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [503])
    dispatcher = one.dispatcher()
    dispatcher.dispatch_due()
    due = dispatcher.delivery("e1", "sub_x")["next_attempt_at"]
    one.clock.set(due - 0.01)
    assert dispatcher.dispatch_due().attempted == 0
    assert len(one.receiver("sub_x").attempts_for("e1")) == 1
    one.clock.set(due)
    assert dispatcher.dispatch_due().delivered == 1


def test_jitter_differs_between_deliveries(one):
    ids = [f"e{i}" for i in range(8)]
    one.add(*[event(i) for i in ids])
    for i in ids:
        one.receiver("sub_x").script_event(i, [500])
    dispatcher = one.dispatcher()
    t = one.clock.time()
    dispatcher.dispatch_due()
    delays = [dispatcher.delivery(i, "sub_x")["next_attempt_at"] - t for i in ids]
    assert all(5 <= x <= 10 for x in delays)
    assert len(set(delays)) > 1


def test_retry_after_is_honoured_exactly(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", ["429:42", "429:900", 200])
    dispatcher = one.dispatcher()
    t = one.clock.time()
    dispatcher.dispatch_due()
    d = dispatcher.delivery("e1", "sub_x")
    assert (d["status"], d["next_attempt_at"]) == ("pending", t + 42)
    assert "429" in d["last_error"]
    one.clock.set(t + 41.5)
    assert dispatcher.dispatch_due().attempted == 0
    one.clock.set(t + 42)
    dispatcher.dispatch_due()
    assert dispatcher.delivery("e1", "sub_x")["next_attempt_at"] == t + 42 + 900  # above the 300 s cap
    one.clock.set(t + 942)
    dispatcher.dispatch_due()
    assert dispatcher.delivery("e1", "sub_x")["status"] == "delivered"


def test_at_most_one_attempt_per_call(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", ["429:0", 200])
    dispatcher = one.dispatcher()
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.failed) == (1, 1)
    assert dispatcher.delivery("e1", "sub_x")["status"] == "pending"
    report = dispatcher.dispatch_due()  # same clock time: due again
    assert (report.attempted, report.delivered) == (1, 1)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410, 422, 301])
def test_non_retryable_response_is_dead_immediately(one, status):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [status])
    dispatcher = one.dispatcher()
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.failed, report.dead) == (1, 0, 1)
    d = dispatcher.delivery("e1", "sub_x")
    assert (d["status"], d["attempts"], d["next_attempt_at"]) == ("dead", 1, None)
    assert str(status) in d["last_error"]
    attempt_until_settled(one, dispatcher)
    assert len(one.receiver("sub_x").attempts_for("e1")) == 1
    (line,) = one.audit()
    assert (line["outcome"], line["status_code"]) == ("dead", status)


@pytest.mark.parametrize("response", [408, 500, 502, 503, 504, "429:5", "drop"])
def test_retryable_failures_are_rescheduled(one, response):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [response])
    dispatcher = one.dispatcher()
    t = one.clock.time()
    dispatcher.dispatch_due()
    d = dispatcher.delivery("e1", "sub_x")
    assert (d["status"], d["attempts"]) == ("pending", 1)
    assert t < d["next_attempt_at"] <= t + 10
    one.clock.set(d["next_attempt_at"])
    dispatcher.dispatch_due()
    assert dispatcher.delivery("e1", "sub_x")["status"] == "delivered"


def test_dead_after_max_attempts(one):
    one.add(event("e1"))
    one.receiver("sub_x").fail_always(503)
    dispatcher = one.dispatcher(max_attempts=3)
    attempt_until_settled(one, dispatcher)
    d = dispatcher.delivery("e1", "sub_x")
    assert (d["status"], d["attempts"], d["next_attempt_at"]) == ("dead", 3, None)
    assert "503" in d["last_error"]
    assert len(one.receiver("sub_x").attempts_for("e1")) == 3
    assert [(a["attempt"], a["outcome"]) for a in one.audit()] == [(1, "failed"), (2, "failed"), (3, "dead")]


def test_default_max_attempts_is_five(one):
    one.add(event("e1"))
    one.receiver("sub_x").fail_always(500)
    dispatcher = one.dispatcher()
    attempt_until_settled(one, dispatcher)
    assert dispatcher.delivery("e1", "sub_x")["attempts"] == 5
    assert len(one.receiver("sub_x").attempts_for("e1")) == 5


def test_rate_limits_count_towards_max_attempts(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", ["429:1", "429:1"])
    dispatcher = one.dispatcher(max_attempts=2)
    attempt_until_settled(one, dispatcher)
    assert dispatcher.delivery("e1", "sub_x")["status"] == "dead"
    assert [a["outcome"] for a in one.audit()] == ["failed", "dead"]


def test_report_counts(one):
    one.add(event("e1"), event("e2"), event("e3"))
    one.receiver("sub_x").script_event("e1", [500])
    one.receiver("sub_x").script_event("e2", [404])
    report = one.dispatcher().dispatch_due()
    assert (report.attempted, report.delivered, report.failed, report.dead) == (3, 1, 1, 1)


def test_failing_subscriber_does_not_block_others(env):
    env.use_subscriptions(TWO_SUBS)
    env.add(*[event(f"e{i}") for i in range(4)])
    env.receiver("sub_x").fail_always(503)
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    assert env.receiver("sub_y").accepted_event_ids() == ["e0", "e1", "e2", "e3"]
    attempt_until_settled(env, dispatcher)
    assert all(dispatcher.delivery(f"e{i}", "sub_x")["status"] == "dead" for i in range(4))
    assert len(env.receiver("sub_y").deliveries) == 4


def test_never_sleeps(one, monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda s: pytest.fail("time.sleep called"))
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", [500, 500])
    dispatcher = one.dispatcher()
    dispatcher.dispatch_due()
    dispatcher.dispatch_due()
    assert one.clock.sleeps == []


@pytest.mark.change
def test_every_request_uses_a_5_second_timeout(env):
    env.add(event("e1"), event("e2"))
    env.receiver("sub_tasks").script_event("e1", [500])
    dispatcher = env.dispatcher()
    dispatcher.dispatch_due()
    env.clock.advance(600)
    dispatcher.dispatch_due()
    assert len(env.requests) == 5
    for request in env.requests:
        timeout = request.extensions["timeout"]
        assert timeout["read"] == 5 and timeout["connect"] == 5, timeout


@pytest.mark.change
def test_timeout_is_retryable(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", ["timeout", 200])
    dispatcher = one.dispatcher()
    t = one.clock.time()
    report = dispatcher.dispatch_due()
    assert (report.attempted, report.failed, report.dead) == (1, 1, 0)
    d = dispatcher.delivery("e1", "sub_x")
    assert d["status"] == "pending" and "Timeout" in d["last_error"]
    assert t + 5 <= d["next_attempt_at"] <= t + 10
    line = one.audit()[0]
    assert (line["outcome"], line["status_code"]) == ("failed", None)
    one.clock.set(d["next_attempt_at"])
    dispatcher.dispatch_due()
    assert dispatcher.delivery("e1", "sub_x")["status"] == "delivered"


@pytest.mark.change
def test_timeouts_count_towards_max_attempts(one):
    one.add(event("e1"))
    one.receiver("sub_x").script_event("e1", ["timeout"] * 3)
    dispatcher = one.dispatcher(max_attempts=3)
    attempt_until_settled(one, dispatcher)
    d = dispatcher.delivery("e1", "sub_x")
    assert (d["status"], d["attempts"]) == ("dead", 3)
