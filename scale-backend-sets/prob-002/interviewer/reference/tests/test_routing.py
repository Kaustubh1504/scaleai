"""Part 1: membership, states, round robin and failover."""

import pytest

from helpers import T0, served, setup, task
from lb.balancer import NoWorkersAvailable, TaskFailed
from lb.models import WorkerState


def test_round_robin_continues_after_last_tried_worker():
    lb, _, (w1, w2, w3) = setup("w1", "w2", "w3")
    w2.kill()
    results = [lb.dispatch(task(f"t{i}")) for i in range(4)]
    assert [(r.worker_id, r.attempts) for r in results] == [("w1", 1), ("w3", 2), ("w1", 1), ("w3", 1)]
    assert lb.worker_state("w2") is WorkerState.UNREACHABLE


def test_membership_changes():
    lb, clock, (w1, w2, w3) = setup("w1", "w2", "w3")
    assert served(lb, 1) == ["w1"]
    lb.remove_worker("w1")
    assert served(lb, 2, "a") == ["w2", "w3"]
    lb.add_worker(w1)
    assert served(lb, 3, "b") == ["w1", "w2", "w3"]
    with pytest.raises(ValueError):
        lb.add_worker(w1)
    with pytest.raises(KeyError):
        lb.remove_worker("ghost")
    with pytest.raises(KeyError):
        lb.worker_state("ghost")


def test_overload_marks_and_expires():
    lb, clock, (w1, w2) = setup("w1", "w2")
    w1.in_flight = w1.capacity
    assert lb.dispatch(task("t")).attempts == 2
    assert lb.worker_state("w1") is WorkerState.OVERLOADED
    w1.in_flight = 0
    clock.set(T0 + 5.0)
    assert served(lb, 1) == ["w1"]


def test_timeouts_fail_over_and_use_task_timeout():
    lb, clock, (w1, w2) = setup("w1", "w2", task_timeout_s=0.25)
    w1.go_silent()
    assert lb.dispatch(task("t")).worker_id == "w2"
    assert clock.time() == T0 + 0.25


def test_task_failure_is_not_retried():
    lb, _, (w1, w2) = setup("w1", "w2")
    with pytest.raises(TaskFailed) as info:
        lb.dispatch(task("bad", poison=True))
    assert info.value.worker_id == "w1" and "poison" in info.value.reason
    assert w2.received == [] and lb.worker_state("w1") is WorkerState.ACTIVE


def test_no_workers():
    lb, _, workers = setup("w1", "w2")
    for w in workers:
        w.kill()
    t = task("t")
    with pytest.raises(NoWorkersAvailable):
        lb.dispatch(t)
    assert t.attempts == 2
    with pytest.raises(NoWorkersAvailable):
        setup()[0].dispatch(task("t"))


def test_unexpected_worker_errors_propagate():
    class Broken:
        worker_id = "b"

        def process(self, payload, timeout=None):
            raise RuntimeError("bug in the client")

        def heartbeat(self):
            return None

    lb, _, _ = setup()
    lb.add_worker(Broken())
    with pytest.raises(RuntimeError):
        lb.dispatch(task("t"))
