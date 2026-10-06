"""Part 2: joining, heartbeats, up/down, failover to the front of the queue."""

import pytest

from conftest import T0, CrashingWorker, states, submit_all, worker_of
from shared.mock_worker import MockWorker, WorkerFleet


# ------------------------------------------------------------------ joining

def test_worker_joining_later_gets_work_first(make_pool, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    pool = make_pool(w1, w2)
    submit_all(pool, "a", "b")
    pool.tick()
    pool.add_worker(w3)
    assert states(pool) == {"w1": "up", "w2": "up", "w3": "up"}
    submit_all(pool, "c", "d", "e")
    pool.tick()
    assert worker_of(pool, "c", "d", "e") == ["w3", "w1", "w2"]


def test_duplicate_add_worker_keeps_the_original(make_pool, make_workers, clock):
    (w1,) = make_workers("w1")
    pool = make_pool(w1)
    impostor = MockWorker("w1", clock=clock)
    with pytest.raises(ValueError):
        pool.add_worker(impostor)
    submit_all(pool, "a")
    pool.tick()
    assert len(w1.received) == 1 and impostor.received == []


def test_joined_worker_counts_as_heard_from_when_it_joins(make_pool, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1)
    clock.set(T0 + 10)
    pool.add_worker(w2)
    clock.set(T0 + 13)
    assert states(pool) == {"w1": "down", "w2": "up"}
    clock.set(T0 + 13.5)
    assert states(pool) == {"w1": "down", "w2": "down"}


# ------------------------------------------------------------------ heartbeats

def test_heartbeats_keep_workers_up(make_pool, make_workers, clock):
    workers = make_workers("w1", "w2")
    pool = make_pool(*workers)
    WorkerFleet(workers, clock=clock).run(10, sink=pool.on_heartbeat)
    assert states(pool) == {"w1": "up", "w2": "up"}
    submit_all(pool, "a", "b")
    assert pool.tick() == 2


def test_timeout_boundary_is_more_than(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1"))
    clock.set(T0 + 3.0)
    assert states(pool) == {"w1": "up"}
    clock.set(T0 + 3.01)
    assert states(pool) == {"w1": "down"}


def test_custom_heartbeat_timeout(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1"), heartbeat_timeout_s=10)
    clock.set(T0 + 9.5)
    assert states(pool) == {"w1": "up"}
    clock.set(T0 + 10.5)
    assert states(pool) == {"w1": "down"}


def test_stale_worker_gets_no_jobs(make_pool, make_workers, clock):
    w1, w2, w3 = workers = make_workers("w1", "w2", "w3")
    pool = make_pool(*workers)
    fleet = WorkerFleet(workers, clock=clock)
    fleet.run(2, sink=pool.on_heartbeat)
    w2.go_silent()
    fleet.run(3, sink=pool.on_heartbeat)
    assert states(pool)["w2"] == "up"  # last heard 3 s ago: not yet more than 3 s
    fleet.run(1, sink=pool.on_heartbeat)
    assert states(pool) == {"w1": "up", "w2": "down", "w3": "up"}
    submit_all(pool, "a", "b", "c", "d")
    assert pool.tick() == 4
    assert w2.received == []
    assert worker_of(pool, "a", "b", "c", "d") == ["w1", "w3", "w1", "w3"]
    assert clock.time() == T0 + 6  # no job was sent to the silent worker, so nothing hung


def test_silent_worker_recovers_on_heartbeat(make_pool, make_workers, clock):
    w1, w2 = workers = make_workers("w1", "w2")
    pool = make_pool(*workers)
    fleet = WorkerFleet(workers, clock=clock)
    w2.go_silent()
    fleet.run(4, sink=pool.on_heartbeat)
    assert states(pool)["w2"] == "down"
    w2.revive()
    fleet.run(1, sink=pool.on_heartbeat)
    assert states(pool)["w2"] == "up"
    submit_all(pool, "a", "b")
    pool.tick()
    assert worker_of(pool, "a", "b") == ["w1", "w2"]


def test_last_heard_uses_the_pool_clock_not_payload_ts(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1"))
    clock.set(T0 + 10)
    pool.on_heartbeat({"worker_id": "w1", "in_flight": 0, "capacity": 4, "ts": 0.0})
    clock.set(T0 + 12)
    assert states(pool) == {"w1": "up"}
    pool.on_heartbeat({"worker_id": "w1", "in_flight": 0, "capacity": 4, "ts": T0 + 1_000_000})
    clock.set(T0 + 15.5)
    assert states(pool) == {"w1": "down"}


def test_minimal_heartbeat_is_valid(make_pool, make_workers, clock):
    pool = make_pool(*make_workers("w1"))
    clock.set(T0 + 2)
    pool.on_heartbeat({"worker_id": "w1"})  # other fields are not checked
    clock.set(T0 + 4.5)
    assert states(pool) == {"w1": "up"}


@pytest.mark.parametrize("payload", [
    None, "w1", ["w1"], {}, {"worker_id": None}, {"worker_id": 1}, {"worker_id": "ghost", "in_flight": 0},
])
def test_malformed_or_unknown_heartbeat_is_ignored(make_pool, make_workers, clock, payload):
    pool = make_pool(*make_workers("w1"))
    clock.set(T0 + 2)
    pool.on_heartbeat(payload)
    assert states(pool) == {"w1": "up"}
    clock.set(T0 + 3.5)
    assert states(pool) == {"w1": "down"}  # the ignored heartbeat did not count as a sign of life


# ------------------------------------------------------------------ failover

def test_spec_example_crash_fails_over_to_the_front(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2)
    submit_all(pool, "a", "b", "c", "d", "e")
    w1.crash_on_next()
    assert pool.tick() == 3
    assert [p["id"] for p in w1.received] == ["a"]  # c was planned on w1 but not sent
    assert pool.pending() == ["a", "c", "e"]
    assert states(pool) == {"w1": "down", "w2": "up"}
    assert [pool.job(i)["attempts"] for i in "abcd"] == [1, 1, 0, 1]
    assert pool.job("a")["status"] == "queued"
    assert pool.tick() == 2
    assert worker_of(pool, "a", "c") == ["w2", "w2"]
    assert pool.job("a")["attempts"] == 2 and pool.job("a")["status"] == "done"
    assert pool.pending() == ["e"]


def test_failover_order_with_two_failing_workers(make_pool, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    pool = make_pool(w1, w2, w3)
    submit_all(pool, *"abcdefgh")
    w2.kill()
    w3.crash_on_next()
    # plan: a,d->w1  b,e->w2  c,f->w3; g,h unplanned
    assert pool.tick() == 4  # a, b (unreachable), c (crash), d; e and f are not sent
    assert pool.pending() == ["b", "c", "e", "f", "g", "h"]
    assert states(pool) == {"w1": "up", "w2": "down", "w3": "down"}
    pool.tick()
    assert worker_of(pool, "b", "c") == ["w1", "w1"] and pool.pending() == ["e", "f", "g", "h"]


def test_killed_worker_is_unreachable_and_job_moves(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, concurrency_per_worker=1)
    w1.kill()
    submit_all(pool, "a", "b")
    assert pool.tick() == 2
    assert pool.pending() == ["a"] and states(pool)["w1"] == "down"
    pool.tick()
    assert pool.job("a")["worker_id"] == "w2" and pool.job("a")["status"] == "done"


def test_hanging_worker_times_out(make_pool, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, concurrency_per_worker=1, job_timeout_s=1.5)
    w1.go_silent()
    submit_all(pool, "a", "b")
    pool.tick()
    assert clock.time() == T0 + 1.5  # the silent worker hung for exactly job_timeout_s
    assert pool.pending() == ["a"] and states(pool)["w1"] == "down"
    pool.tick()
    assert pool.job("a")["worker_id"] == "w2" and pool.job("a")["status"] == "done"
    assert clock.sleeps == []


def test_slow_worker_times_out_then_rejoins_on_heartbeat(make_pool, clock):
    slow = MockWorker("w1", latency_s=1.0, clock=clock)
    pool = make_pool(slow, job_timeout_s=2.0)
    slow.slow(5)  # 5 s per job
    submit_all(pool, "a")
    pool.tick()
    assert states(pool) == {"w1": "down"} and pool.pending() == ["a"]
    assert pool.tick() == 0  # still down: no heartbeat yet
    slow.revive()
    pool.on_heartbeat(slow.heartbeat())
    assert states(pool) == {"w1": "up"}
    pool.tick()
    assert pool.job("a")["status"] == "done" and pool.job("a")["attempts"] == 2


def test_down_after_failure_until_next_heartbeat(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2)
    w1.kill()
    submit_all(pool, "a")
    pool.tick()
    assert states(pool)["w1"] == "down"  # although it was heard from (registered) 0 s ago
    w1.revive()  # alive again, but the pool has not heard from it
    submit_all(pool, "b", "c")
    pool.tick()
    assert worker_of(pool, "a", "b") == ["w2", "w2"] and pool.pending() == ["c"]
    assert w1.received == []  # a dead worker refuses the connection, so nothing ever reached it
    pool.on_heartbeat(w1.heartbeat())
    assert states(pool)["w1"] == "up"
    pool.tick()
    assert worker_of(pool, "c") == ["w1"]


def test_overloaded_worker_refuses_but_stays_up(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2)
    w1.in_flight = w1.capacity
    submit_all(pool, "a", "b", "c", "d")
    assert pool.tick() == 3  # a refused; c (also planned on w1) not sent; b, d done
    assert pool.pending() == ["a", "c"]
    assert states(pool) == {"w1": "up", "w2": "up"}
    assert pool.job("a")["attempts"] == 1 and pool.job("a")["status"] == "queued"
    w1.in_flight = 0
    pool.run_until_idle()
    assert pool.pending() == [] and pool.job("c")["status"] == "done"


def test_failover_never_fails_a_job_and_leaves_tasks_failed_alone(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, concurrency_per_worker=1, max_attempts=1)
    w1.crash_on_next()
    submit_all(pool, "a")
    submit_all(pool, "bad", fail=True)
    pool.tick()
    assert pool.job("a")["status"] == "queued" and pool.job("bad")["status"] == "failed"
    assert pool.pending() == ["a"]
    pool.tick()
    assert pool.job("a")["status"] == "done"


def test_whole_fleet_down_keeps_jobs_queued(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2)
    w1.kill()
    w2.kill()
    submit_all(pool, "a", "b", "c")
    assert pool.run_until_idle() == 2
    assert pool.pending() == ["a", "b", "c"]
    assert pool.status()["queued"] == 3 and states(pool) == {"w1": "down", "w2": "down"}
    w2.revive()
    pool.on_heartbeat(w2.heartbeat())
    pool.run_until_idle()
    assert pool.pending() == [] and pool.status()["done"] == 3


def test_other_exceptions_propagate(make_pool):
    class Buggy:
        worker_id = "b1"

        def process(self, payload, timeout=None):
            raise KeyError("bug in the client library")

        def heartbeat(self):
            return None

    pool = make_pool(Buggy())
    submit_all(pool, "a")
    with pytest.raises(KeyError):
        pool.tick()


# ------------------------------------------------------------------ mid-part change: pinned jobs

@pytest.mark.change
def test_pinned_job_runs_only_on_its_worker(make_pool, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    pool = make_pool(w1, w2, w3, concurrency_per_worker=1)
    assert pool.submit("p", {"id": "p"}, pinned_worker="w3") is True
    submit_all(pool, "a", "b")
    pool.tick()
    assert worker_of(pool, "p", "a", "b") == ["w3", "w1", "w2"]


@pytest.mark.change
def test_pinned_job_waits_while_its_worker_is_down(make_pool, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2)
    w2.kill()
    fleet = WorkerFleet([w1, w2], clock=clock)
    fleet.run(4, sink=pool.on_heartbeat)
    pool.submit("p", {"id": "p"}, pinned_worker="w2")
    submit_all(pool, "a", "b")
    pool.tick()
    assert pool.pending() == ["p"] and w2.received == []
    assert worker_of(pool, "a", "b") == ["w1", "w1"]
    w2.revive()
    fleet.run(1, sink=pool.on_heartbeat)
    pool.tick()
    assert worker_of(pool, "p") == ["w2"] and pool.pending() == []


@pytest.mark.change
def test_pinned_job_waits_when_its_worker_is_full(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, concurrency_per_worker=1)
    pool.submit("p1", {"id": "p1"}, pinned_worker="w1")
    pool.submit("p2", {"id": "p2"}, pinned_worker="w1")
    submit_all(pool, "a")
    assert pool.tick() == 2
    assert worker_of(pool, "p1", "a") == ["w1", "w2"] and pool.pending() == ["p2"]
    pool.tick()
    assert worker_of(pool, "p2") == ["w1"]


@pytest.mark.change
def test_pinned_to_unknown_worker_waits_until_it_joins(make_pool, make_workers, clock):
    (w1,) = make_workers("w1")
    pool = make_pool(w1)
    pool.submit("p", {"id": "p"}, pinned_worker="w9")
    submit_all(pool, "a")
    assert pool.run_until_idle() == 1
    assert pool.pending() == ["p"]
    pool.add_worker(CrashingWorker("w9", clock=clock))
    pool.tick()
    assert worker_of(pool, "p") == ["w9"]


@pytest.mark.change
def test_pinned_job_fails_over_to_the_front_and_waits(make_pool, make_workers):
    w1, w2 = make_workers("w1", "w2")
    pool = make_pool(w1, w2, concurrency_per_worker=1)
    w2.crash_on_next()
    pool.submit("p", {"id": "p"}, pinned_worker="w2")
    submit_all(pool, "a", "b")
    pool.tick()
    assert pool.pending() == ["p", "b"]
    pool.run_until_idle()
    assert pool.pending() == ["p"] and pool.job("p")["attempts"] == 1
    w2.revive()
    pool.on_heartbeat(w2.heartbeat())
    pool.tick()
    assert pool.job("p")["status"] == "done" and pool.job("p")["worker_id"] == "w2"
