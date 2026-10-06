import pytest

from lb.health import WorkerHealth, parse_heartbeat, reports_overload
from lb.models import WorkerState


@pytest.mark.parametrize("in_flight, capacity, expected", [
    (0, 4, False), (3, 4, False), (4, 5, True), (79, 100, False), (80, 100, True), (5, 4, True), (1, 1, True),
])
def test_reports_overload_at_80_percent(in_flight, capacity, expected):
    assert reports_overload(in_flight, capacity) is expected


@pytest.mark.parametrize("payload", [
    None, [], {}, {"worker_id": 1, "in_flight": 0, "capacity": 1}, {"worker_id": "w", "in_flight": True, "capacity": 4},
    {"worker_id": "w", "in_flight": 0.5, "capacity": 4}, {"worker_id": "w", "in_flight": 0, "capacity": 0},
    {"worker_id": "w", "in_flight": -1, "capacity": 4},
])
def test_parse_heartbeat_rejects_malformed(payload):
    assert parse_heartbeat(payload) is None


def test_parse_heartbeat_ignores_extra_keys():
    assert parse_heartbeat({"worker_id": "w", "in_flight": 1, "capacity": 4, "ts": 9, "x": 1}) == ("w", 1, 4)


def test_overload_cooldown_and_heartbeat_override():
    health = WorkerHealth(seq=0, last_seen=0.0)
    health.mark_overloaded(10.0, 5.0)
    assert health.current(14.9) is WorkerState.OVERLOADED
    assert health.current(15.0) is WorkerState.ACTIVE
    health.mark_overloaded(20.0, 5.0)
    health.record_heartbeat(21.0, 0, 4, 5.0)
    assert health.current(21.0) is WorkerState.ACTIVE and health.last_seen == 21.0


def test_staleness_is_strictly_older_than_timeout():
    health = WorkerHealth(seq=0, last_seen=100.0)
    assert not health.is_stale(103.0, 3.0)
    assert health.is_stale(103.5, 3.0)
