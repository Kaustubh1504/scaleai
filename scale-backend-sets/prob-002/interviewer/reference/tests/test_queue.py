"""Part 3: priority queue, drain and the attempt budget."""

import pytest

from helpers import setup, task


def test_priority_order_fifo_and_duplicates():
    lb, _, _ = setup("w1")
    for task_id, priority in [("low", -1), ("a", 2), ("b", 2), ("top", 7)]:
        lb.submit(task(task_id, priority))
    with pytest.raises(ValueError):
        lb.submit(task("a"))
    assert [t.id for t in lb.pending()] == ["top", "a", "b", "low"]
    assert [r.task_id for r in lb.drain()] == ["top", "a", "b", "low"]


def test_nothing_lost_when_workers_are_down():
    lb, _, (w1,) = setup("w1")
    w1.kill()
    first, second = task("first", 1), task("second")
    lb.submit(first)
    lb.submit(second)
    assert lb.drain() == []
    assert [t.id for t in lb.pending()] == ["first", "second"] and first.attempts == 1
    w1.revive()
    lb.on_heartbeat(w1.heartbeat())
    assert [(r.task_id, r.attempts) for r in lb.drain()] == [("first", 2), ("second", 1)]


def test_budget_exhaustion_and_task_failure_go_to_failed():
    lb, _, (w1, w2, w3) = setup("w1", "w2", "w3", max_attempts=2)
    w1.kill()
    w2.kill()
    doomed, poison, fine = task("doomed", 3), task("poison", 2, poison=True), task("fine", 1)
    for t in (doomed, poison, fine):
        lb.submit(t)
    results = lb.drain()
    assert [(t.id, t.attempts) for t, _ in lb.failed] == [("doomed", 2), ("poison", 1)]
    assert all(reason for _, reason in lb.failed)
    assert [(r.task_id, r.worker_id) for r in results] == [("fine", "w3")]
    assert lb.pending() == []


def test_unexpected_error_leaves_task_queued():
    class Broken:
        worker_id = "b"

        def process(self, payload, timeout=None):
            raise RuntimeError("boom")

        def heartbeat(self):
            return None

    lb, _, _ = setup()
    lb.add_worker(Broken())
    lb.submit(task("t"))
    with pytest.raises(RuntimeError):
        lb.drain()
    assert [t.id for t in lb.pending()] == ["t"]
