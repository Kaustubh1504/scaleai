"""Part 2: heartbeats and health checks."""

from helpers import T0, served, setup
from lb.models import WorkerState
from mock_services.workers import WorkerFleet


def test_stale_workers_become_unreachable_and_recover():
    lb, clock, (w1, w2) = setup("w1", "w2")
    fleet = WorkerFleet([w1, w2], clock=clock)
    fleet.run(2, sink=lb.on_heartbeat)
    w2.go_silent()
    fleet.run(4, sink=lb.on_heartbeat)
    lb.check_health()
    assert lb.worker_state("w2") is WorkerState.UNREACHABLE
    assert served(lb, 2) == ["w1", "w1"]
    w2.revive()
    fleet.run(1, sink=lb.on_heartbeat)
    assert lb.worker_state("w2") is WorkerState.ACTIVE


def test_registration_counts_as_last_seen():
    lb, clock, _ = setup("w1")
    clock.set(T0 + 3.0)
    lb.check_health()
    assert lb.worker_state("w1") is WorkerState.ACTIVE
    clock.set(T0 + 3.01)
    lb.check_health()
    assert lb.worker_state("w1") is WorkerState.UNREACHABLE


def test_heartbeat_load_drives_overload():
    lb, clock, (w1,) = setup("w1")
    lb.on_heartbeat({"worker_id": "w1", "in_flight": 4, "capacity": 5, "ts": 0})
    assert lb.worker_state("w1") is WorkerState.OVERLOADED
    lb.on_heartbeat({"worker_id": "w1", "in_flight": 3, "capacity": 5, "ts": 0})
    assert lb.worker_state("w1") is WorkerState.ACTIVE


def test_unknown_and_malformed_heartbeats_are_ignored():
    lb, clock, _ = setup("w1")
    for payload in ({"worker_id": "ghost", "in_flight": 0, "capacity": 1}, {"worker_id": "w1"}, None):
        lb.on_heartbeat(payload)
    clock.set(T0 + 4)
    lb.check_health()
    assert lb.worker_state("w1") is WorkerState.UNREACHABLE
