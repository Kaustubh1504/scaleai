"""Part 2: joining, heartbeats, up/down and failover."""

import pytest

from helpers import T0, setup, submit, worker_of
from mock_services.workers import MockWorker, WorkerFleet


def workers_state(pool):
    return pool.status()["workers"]


def test_crash_mid_job_fails_over_to_the_front_as_in_the_spec_example():
    pool, _, (w1, w2) = setup("w1", "w2")
    submit(pool, "a", "b", "c", "d", "e")
    w1.crash_on_next()
    assert pool.tick() == 3
    assert pool.pending() == ["a", "c", "e"]
    assert workers_state(pool) == {"w1": "down", "w2": "up"}
    assert [pool.job(i)["attempts"] for i in "ac"] == [1, 0]
    pool.tick()
    assert worker_of(pool, "a", "c") == ["w2", "w2"] and pool.pending() == ["e"]
    assert pool.job("a")["attempts"] == 2


def test_hanging_worker_times_out_and_moves_the_clock():
    pool, clock, (w1, w2) = setup("w1", "w2", concurrency_per_worker=1, job_timeout_s=1.5)
    w1.go_silent()
    submit(pool, "a", "b")
    pool.tick()
    assert clock.time() == T0 + 1.5 and clock.sleeps == []
    assert pool.pending() == ["a"] and workers_state(pool)["w1"] == "down"
    pool.tick()
    assert pool.job("a")["status"] == "done" and pool.job("a")["worker_id"] == "w2"


def test_overloaded_worker_refuses_but_stays_up():
    pool, _, (w1, w2) = setup("w1", "w2", concurrency_per_worker=2)
    w1.in_flight = w1.capacity
    submit(pool, "a", "b", "c")
    assert pool.tick() == 2  # c, planned on w1 after a was refused, is not sent
    assert pool.pending() == ["a", "c"] and workers_state(pool)["w1"] == "up"
    w1.in_flight = 0
    pool.run_until_idle()
    assert pool.pending() == [] and pool.job("a")["attempts"] == 2


def test_heartbeat_staleness_and_recovery():
    pool, clock, (w1, w2, w3) = setup("w1", "w2", "w3")
    fleet = WorkerFleet([w1, w2, w3], clock=clock)
    fleet.run(2, sink=pool.on_heartbeat)
    w2.go_silent()
    fleet.run(3, sink=pool.on_heartbeat)
    assert workers_state(pool)["w2"] == "up"  # exactly 3 s: not more than the timeout
    fleet.run(1, sink=pool.on_heartbeat)
    assert workers_state(pool)["w2"] == "down"
    submit(pool, "a", "b", "c")
    pool.tick()
    assert w2.received == [] and set(worker_of(pool, "a", "b", "c")) == {"w1", "w3"}
    w2.revive()
    fleet.run(1, sink=pool.on_heartbeat)
    submit(pool, "d")
    pool.tick()
    assert worker_of(pool, "d") == ["w2"]  # back, and the fewest calls so far


def test_heartbeat_uses_pool_clock_and_bad_payloads_are_ignored():
    pool, clock, _ = setup("w1")
    clock.set(T0 + 10)
    pool.on_heartbeat({"worker_id": "w1", "ts": 0})
    clock.set(T0 + 12)
    assert workers_state(pool) == {"w1": "up"}
    for bad in (None, "w1", {}, {"worker_id": 1}, {"worker_id": "ghost"}):
        pool.on_heartbeat(bad)
    clock.set(T0 + 13.5)
    assert workers_state(pool) == {"w1": "down"}


def test_killed_worker_rejoins_on_heartbeat_and_new_worker_joins():
    pool, clock, (w1,) = setup("w1")
    w1.kill()
    submit(pool, "a")
    pool.tick()
    assert workers_state(pool) == {"w1": "down"} and pool.pending() == ["a"]
    w1.revive()
    pool.on_heartbeat(w1.heartbeat())
    assert workers_state(pool) == {"w1": "up"}
    late = MockWorker("w2", clock=clock)
    pool.add_worker(late)
    with pytest.raises(ValueError):
        pool.add_worker(MockWorker("w2", clock=clock))
    assert pool.tick() == 1 and worker_of(pool, "a") == ["w2"]  # fewest earlier calls wins


@pytest.mark.parametrize("pin, expected", [("w2", "w2"), ("w1", "w1")])
def test_pinned_job_runs_only_on_its_worker(pin, expected):
    pool, _, (w1, w2) = setup("w1", "w2", concurrency_per_worker=1)
    pool.submit("p", {"id": "p"}, pinned_worker=pin)
    pool.tick()
    assert worker_of(pool, "p") == [expected]


def test_pinned_job_waits_in_place_and_does_not_block():
    pool, clock, (w1, w2) = setup("w1", "w2", concurrency_per_worker=1)
    pool.submit("p", {"id": "p"}, pinned_worker="w9")
    submit(pool, "a", "b")
    pool.tick()
    assert pool.pending() == ["p"]
    pool.add_worker(MockWorker("w9", clock=clock))
    pool.tick()
    assert worker_of(pool, "p") == ["w9"]
