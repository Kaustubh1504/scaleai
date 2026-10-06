"""Part 2: heartbeats, staleness detection and recovery."""

import pytest

from conftest import T0, hb, served_by, task
from lb.models import WorkerState
from shared.mock_worker import MockWorker, WorkerFleet

ACTIVE, OVERLOADED, UNREACHABLE = WorkerState.ACTIVE, WorkerState.OVERLOADED, WorkerState.UNREACHABLE


def states(lb, *ids):
    return [lb.worker_state(i) for i in ids]


def test_heartbeats_keep_workers_active(make_lb, make_workers, clock):
    workers = make_workers("w1", "w2")
    lb = make_lb(*workers)
    WorkerFleet(workers, clock=clock).run(10, sink=lb.on_heartbeat)
    lb.check_health()
    assert states(lb, "w1", "w2") == [ACTIVE, ACTIVE]


def test_worker_that_never_heartbeats_goes_unreachable(make_lb, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    lb = make_lb(w1, w2)
    WorkerFleet([w1], clock=clock).run(5, sink=lb.on_heartbeat)
    lb.check_health()
    assert states(lb, "w1", "w2") == [ACTIVE, UNREACHABLE]
    assert served_by(lb, 3) == ["w1"] * 3


def test_heartbeat_timeout_boundary(make_lb, make_workers, clock):
    lb = make_lb(*make_workers("w1"))
    clock.set(T0 + 3.0)
    lb.check_health()
    assert lb.worker_state("w1") is ACTIVE  # exactly 3 s is not older than 3 s
    clock.set(T0 + 3.5)
    lb.check_health()
    assert lb.worker_state("w1") is UNREACHABLE


def test_custom_heartbeat_timeout(make_lb, make_workers, clock):
    lb = make_lb(*make_workers("w1"), heartbeat_timeout_s=10.0)
    clock.set(T0 + 9.0)
    lb.check_health()
    assert lb.worker_state("w1") is ACTIVE


def test_last_seen_uses_the_balancer_clock_not_payload_ts(make_lb, make_workers, clock):
    lb = make_lb(*make_workers("w1"))
    clock.set(T0 + 10)
    lb.on_heartbeat(hb("w1", ts=0.0))
    clock.set(T0 + 12)
    lb.check_health()
    assert lb.worker_state("w1") is ACTIVE
    lb.on_heartbeat(hb("w1", ts=T0 + 1_000_000))
    clock.set(T0 + 20)
    lb.check_health()
    assert lb.worker_state("w1") is UNREACHABLE


def test_silent_worker_is_detected_and_recovers(make_lb, make_workers, clock):
    w1, w2, w3 = workers = make_workers("w1", "w2", "w3")
    lb = make_lb(*workers)
    fleet = WorkerFleet(workers, clock=clock)
    fleet.run(2, sink=lb.on_heartbeat)
    w2.go_silent()
    fleet.run(3, sink=lb.on_heartbeat)
    lb.check_health()
    assert lb.worker_state("w2") is ACTIVE  # last heartbeat 3 s ago: not yet stale
    fleet.run(1, sink=lb.on_heartbeat)
    lb.check_health()
    assert states(lb, "w1", "w2", "w3") == [ACTIVE, UNREACHABLE, ACTIVE]
    assert "w2" not in served_by(lb, 4)
    w2.revive()
    fleet.run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w2") is ACTIVE
    assert "w2" in served_by(lb, 3, "u")


def test_failed_over_worker_recovers_on_heartbeat(make_lb, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    w1.kill()
    lb = make_lb(w1, w2)
    assert served_by(lb, 1) == ["w2"]
    fleet = WorkerFleet([w1, w2], clock=clock)
    fleet.run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w1") is UNREACHABLE  # dead workers send no heartbeats
    w1.revive()
    lb.check_health()
    assert lb.worker_state("w1") is UNREACHABLE  # check_health never brings a worker back
    fleet.run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w1") is ACTIVE
    assert served_by(lb, 2, "u") == ["w1", "w2"]


def test_full_heartbeat_marks_overloaded_and_a_lighter_one_clears_it(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    lb = make_lb(w1, w2)
    lb.on_heartbeat(hb("w1", in_flight=4, capacity=4))
    assert lb.worker_state("w1") is OVERLOADED
    assert served_by(lb, 2) == ["w2", "w2"]
    assert w1.received == []
    lb.on_heartbeat(hb("w1", in_flight=3, capacity=4))
    assert lb.worker_state("w1") is ACTIVE  # immediately, without waiting for the cooldown
    lb.on_heartbeat(hb("w1", in_flight=6, capacity=4))
    assert lb.worker_state("w1") is OVERLOADED
    lb.on_heartbeat(hb("w1", in_flight=0, capacity=4))
    assert lb.worker_state("w1") is ACTIVE


def test_heartbeat_overload_expires_after_cooldown(make_lb, make_workers, clock):
    lb = make_lb(*make_workers("w1"))
    lb.on_heartbeat(hb("w1", in_flight=4, capacity=4))
    clock.set(T0 + 4.9)
    assert lb.worker_state("w1") is OVERLOADED
    clock.set(T0 + 5.0)
    assert lb.worker_state("w1") is ACTIVE


def test_heartbeat_clears_overload_from_dispatch(make_lb, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    w1.in_flight = w1.capacity
    lb = make_lb(w1, w2)
    assert lb.dispatch(task("t1")).worker_id == "w2"
    assert lb.worker_state("w1") is OVERLOADED
    w1.in_flight = 0
    WorkerFleet([w1, w2], clock=clock).run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w1") is ACTIVE


def test_full_heartbeat_from_unreachable_worker_makes_it_overloaded(make_lb, make_workers, clock):
    lb = make_lb(*make_workers("w1"))
    clock.set(T0 + 5)
    lb.check_health()
    assert lb.worker_state("w1") is UNREACHABLE
    lb.on_heartbeat(hb("w1", in_flight=4, capacity=4))
    assert lb.worker_state("w1") is OVERLOADED
    lb.on_heartbeat(hb("w1", in_flight=0, capacity=4))
    assert lb.worker_state("w1") is ACTIVE


@pytest.mark.parametrize("payload", [
    hb("ghost"),
    {},
    {"worker_id": "w1"},
    {"worker_id": "w1", "in_flight": "2", "capacity": 4},
    {"worker_id": "w1", "in_flight": 1, "capacity": 0},
    {"worker_id": "w1", "in_flight": -1, "capacity": 4},
    None,
    "w1",
])
def test_unknown_or_malformed_heartbeat_is_ignored(make_lb, make_workers, clock, payload):
    lb = make_lb(*make_workers("w1"))
    clock.set(T0 + 2)
    lb.on_heartbeat(payload)
    assert lb.worker_state("w1") is ACTIVE
    clock.set(T0 + 3.5)
    lb.check_health()
    assert lb.worker_state("w1") is UNREACHABLE  # the ignored heartbeat did not count as a sign of life


def test_heartbeat_from_removed_worker_is_ignored(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    lb = make_lb(w1, w2)
    lb.remove_worker("w1")
    lb.on_heartbeat(w1.heartbeat())
    with pytest.raises(KeyError):
        lb.worker_state("w1")
    assert served_by(lb, 2) == ["w2", "w2"]


@pytest.mark.change
@pytest.mark.parametrize("in_flight, capacity, expected", [
    (4, 5, OVERLOADED), (3, 5, ACTIVE), (8, 10, OVERLOADED), (7, 10, ACTIVE), (79, 100, ACTIVE),
    (80, 100, OVERLOADED), (3, 4, ACTIVE), (1, 1, OVERLOADED), (0, 1, ACTIVE),
])
def test_overloaded_at_80_percent(make_lb, make_workers, in_flight, capacity, expected):
    lb = make_lb(*make_workers("w1"))
    lb.on_heartbeat(hb("w1", in_flight=in_flight, capacity=capacity))
    assert lb.worker_state("w1") is expected


@pytest.mark.change
def test_80_percent_heartbeat_diverts_traffic(make_lb, make_workers, clock):
    busy = MockWorker("w1", capacity=5, clock=clock)
    (w2,) = make_workers("w2")
    busy.in_flight = 4  # it would still accept a task
    lb = make_lb(busy, w2)
    WorkerFleet([busy, w2], clock=clock).run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w1") is OVERLOADED
    assert served_by(lb, 2) == ["w2", "w2"]
    assert busy.received == []
    busy.in_flight = 3
    WorkerFleet([busy, w2], clock=clock).run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w1") is ACTIVE
