"""Part 3: priority queue, drain, attempt budget and failed tasks."""

import pytest

from conftest import T0, task
from lb.models import WorkerState
from shared.mock_worker import WorkerFleet

ACTIVE, UNREACHABLE = WorkerState.ACTIVE, WorkerState.UNREACHABLE


def ids(tasks):
    return [t.id for t in tasks]


def summary(results):
    return [(r.task_id, r.worker_id, r.attempts) for r in results]


def test_highest_priority_first_fifo_within_priority(make_lb, make_workers):
    lb = make_lb(*make_workers("w1", "w2"))
    for task_id, priority in [("a", 1), ("b", 5), ("c", 1), ("d", 5), ("e", -1), ("f", 3)]:
        lb.submit(task(task_id, priority))
    assert ids(lb.pending()) == ["b", "d", "f", "a", "c", "e"]
    results = lb.drain()
    assert [r.task_id for r in results] == ["b", "d", "f", "a", "c", "e"]
    assert [r.worker_id for r in results] == ["w1", "w2"] * 3
    assert results[0].result == {"task_id": "b", "worker_id": "w1", "status": "done"}
    assert lb.pending() == [] and lb.failed == []
    assert lb.drain() == []


def test_submit_and_pending_do_not_dispatch(make_lb, make_workers):
    (w1,) = make_workers("w1")
    lb = make_lb(w1)
    lb.submit(task("a"))
    snapshot = lb.pending()
    snapshot.clear()
    assert ids(lb.pending()) == ["a"]
    assert w1.received == []


def test_duplicate_pending_id_is_rejected(make_lb, make_workers):
    lb = make_lb(*make_workers("w1"))
    lb.submit(task("a"))
    with pytest.raises(ValueError):
        lb.submit(task("a", priority=9))
    assert [(t.id, t.priority) for t in lb.pending()] == [("a", 0)]
    lb.drain()
    lb.submit(task("a"))  # allowed again once it has left the queue
    assert ids(lb.pending()) == ["a"]


def test_no_workers_leaves_queue_intact(make_lb, make_workers):
    lb = make_lb()
    for task_id, priority in [("a", 1), ("b", 2), ("c", 1)]:
        lb.submit(task(task_id, priority))
    assert lb.drain() == []
    assert ids(lb.pending()) == ["b", "a", "c"]
    assert lb.failed == []
    lb.add_worker(make_workers("w1")[0])
    assert [r.task_id for r in lb.drain()] == ["b", "a", "c"]
    assert lb.pending() == []


def test_attempts_carry_over_between_drains(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    w1.kill()
    w2.kill()
    lb = make_lb(w1, w2)
    a, b = task("a", 2), task("b", 1)
    lb.submit(a)
    lb.submit(b)
    assert lb.drain() == []
    assert (a.attempts, b.attempts) == (2, 0)  # drain stopped at a; b was never tried
    assert ids(lb.pending()) == ["a", "b"] and lb.failed == []
    w1.revive()
    lb.on_heartbeat(w1.heartbeat())
    assert summary(lb.drain()) == [("a", "w1", 3), ("b", "w1", 1)]
    assert lb.pending() == []


def test_task_fails_after_max_attempts_across_drains(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    w1.kill()
    w2.kill()
    lb = make_lb(w1, w2)
    a, b = task("a", 5), task("b", 1)
    lb.submit(a)
    lb.submit(b)
    assert lb.drain() == [] and a.attempts == 2
    w1.revive()
    w2.revive()
    lb.on_heartbeat(w1.heartbeat())
    lb.on_heartbeat(w2.heartbeat())
    w1.kill()
    results = lb.drain()
    # a: third attempt on w1 fails -> budget used up, so w2 is not tried for it; b then goes to w2.
    assert [(t.id, t.attempts) for t, _ in lb.failed] == [("a", 3)]
    reason = lb.failed[0][1]
    assert isinstance(reason, str) and reason
    assert summary(results) == [("b", "w2", 1)]
    assert w2.received == [{"id": "b"}]
    assert lb.pending() == []


def test_max_attempts_caps_a_single_drain(make_lb, make_workers):
    workers = make_workers("w1", "w2", "w3", "w4", "w5")
    for w in workers[:3]:
        w.kill()
    lb = make_lb(*workers, max_attempts=3)
    a, b = task("a", 1), task("b", 0)
    lb.submit(a)
    lb.submit(b)
    results = lb.drain()
    assert ids(t for t, _ in lb.failed) == ["a"] and a.attempts == 3
    assert summary(results) == [("b", "w4", 1)]
    assert workers[3].received == [{"id": "b"}]  # a never reached w4
    assert [lb.worker_state(w.worker_id) for w in workers] == [UNREACHABLE] * 3 + [ACTIVE] * 2


def test_custom_max_attempts(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    w1.kill()
    lb = make_lb(w1, w2, max_attempts=1)
    a = task("a")
    lb.submit(a)
    assert lb.drain() == []
    assert ids(t for t, _ in lb.failed) == ["a"] and a.attempts == 1


def test_task_failure_goes_straight_to_failed(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    lb = make_lb(w1, w2)
    poison = task("poison", 9, poison=True)
    lb.submit(poison)
    lb.submit(task("ok", 1))
    results = lb.drain()
    assert summary(results) == [("ok", "w2", 1)]
    assert len(lb.failed) == 1 and lb.failed[0][0] is poison
    assert isinstance(lb.failed[0][1], str) and lb.failed[0][1]
    assert poison.attempts == 1 and lb.pending() == []
    assert lb.worker_state("w1") is ACTIVE
    lb.submit(task("bad2", poison=True))
    assert lb.drain() == []
    assert ids(t for t, _ in lb.failed) == ["poison", "bad2"]


def test_drain_with_heartbeats_and_a_hanging_worker(make_lb, make_workers, clock):
    w1, w2, w3 = workers = make_workers("w1", "w2", "w3")
    lb = make_lb(*workers)
    fleet = WorkerFleet(workers, clock=clock)
    fleet.run(1, sink=lb.on_heartbeat)
    for i in range(6):
        lb.submit(task(f"t{i}", priority=i % 2))
    w2.go_silent()
    results = lb.drain()
    assert summary(results) == [("t1", "w1", 1), ("t3", "w3", 2), ("t5", "w1", 1),
                                ("t0", "w3", 1), ("t2", "w1", 1), ("t4", "w3", 1)]
    assert clock.time() == T0 + 1 + 2.0  # one timeout on w2
    fleet.run(2, sink=lb.on_heartbeat)
    lb.check_health()
    assert lb.worker_state("w2") is UNREACHABLE
    w2.revive()
    fleet.run(1, sink=lb.on_heartbeat)
    lb.submit(task("x"))
    lb.submit(task("y"))
    assert summary(lb.drain()) == [("x", "w1", 1), ("y", "w2", 1)]
    assert lb.failed == [] and lb.pending() == []
