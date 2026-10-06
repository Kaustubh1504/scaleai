"""Part 1: membership, worker states, state-aware round robin and failover."""

import pytest

from conftest import T0, served_by, task
from lb.balancer import DispatchResult, NoWorkersAvailable, TaskFailed
from lb.models import Task, WorkerState
from shared.mock_worker import MockWorker

ACTIVE, OVERLOADED, UNREACHABLE = WorkerState.ACTIVE, WorkerState.OVERLOADED, WorkerState.UNREACHABLE


def test_round_robin_in_registration_order(make_lb, make_workers):
    lb = make_lb(*make_workers("w1", "w2", "w3"))
    results = [lb.dispatch(task(f"t{i}")) for i in range(6)]
    assert [r.worker_id for r in results] == ["w1", "w2", "w3"] * 2
    first = results[0]
    assert isinstance(first, DispatchResult)
    assert (first.task_id, first.attempts) == ("t0", 1)
    assert first.result == {"task_id": "t0", "worker_id": "w1", "status": "done"}


def test_sends_payload_with_task_timeout(make_lb):
    class Recorder:
        worker_id = "r1"

        def __init__(self):
            self.calls = []

        def process(self, payload, timeout=None):
            self.calls.append((payload, timeout))
            return "ok"

        def heartbeat(self):
            return None

    worker = Recorder()
    lb = make_lb(worker, task_timeout_s=1.5)
    assert lb.dispatch(Task(id="x", payload={"a": 1})).result == "ok"
    assert worker.calls == [({"a": 1}, 1.5)]


def test_workers_start_active_and_unknown_is_key_error(make_lb, make_workers):
    lb = make_lb(*make_workers("w1", "w2"))
    assert lb.worker_state("w1") is ACTIVE and lb.worker_state("w2") is ACTIVE
    with pytest.raises(KeyError):
        lb.worker_state("nope")


def test_worker_joining_later_enters_rotation(make_lb, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    lb = make_lb(w1, w2)
    assert served_by(lb, 2) == ["w1", "w2"]
    lb.add_worker(w3)
    assert lb.worker_state("w3") is ACTIVE
    assert served_by(lb, 3, "u") == ["w3", "w1", "w2"]


def test_duplicate_worker_id_is_rejected(make_lb, make_workers, clock):
    original, other = make_workers("w1", "w2")
    lb = make_lb(original, other)
    impostor = MockWorker("w1", clock=clock)
    with pytest.raises(ValueError):
        lb.add_worker(impostor)
    assert served_by(lb, 2) == ["w1", "w2"]
    assert len(original.received) == 1 and impostor.received == []


def test_removed_worker_gets_no_more_tasks(make_lb, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    lb = make_lb(w1, w2, w3)
    assert served_by(lb, 1) == ["w1"]
    lb.remove_worker("w1")  # the most recently tried worker: rotation continues after it
    assert served_by(lb, 3, "u") == ["w2", "w3", "w2"]
    assert len(w1.received) == 1
    with pytest.raises(KeyError):
        lb.worker_state("w1")


def test_remove_unknown_worker_is_key_error(make_lb, make_workers):
    lb = make_lb(*make_workers("w1"))
    with pytest.raises(KeyError):
        lb.remove_worker("nope")
    lb.remove_worker("w1")
    with pytest.raises(KeyError):
        lb.remove_worker("w1")


def test_re_added_worker_goes_to_the_end(make_lb, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    lb = make_lb(w1, w2, w3)
    lb.remove_worker("w1")
    lb.add_worker(w1)
    assert lb.worker_state("w1") is ACTIVE
    assert served_by(lb, 3) == ["w2", "w3", "w1"]


def test_full_worker_is_marked_overloaded_and_skipped(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    w1.in_flight = w1.capacity
    lb = make_lb(w1, w2)
    result = lb.dispatch(task("t1"))
    assert (result.worker_id, result.attempts) == ("w2", 2)
    assert lb.worker_state("w1") is OVERLOADED and lb.worker_state("w2") is ACTIVE
    w1.in_flight = 0  # it has room again, but the cooldown has not passed
    assert served_by(lb, 3, "u") == ["w2", "w2", "w2"]
    assert w1.received == []


def test_overload_cooldown(make_lb, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    w1.in_flight = w1.capacity
    lb = make_lb(w1, w2)
    lb.dispatch(task("t1"))
    w1.in_flight = 0
    clock.set(T0 + 4.9)
    assert lb.worker_state("w1") is OVERLOADED
    clock.set(T0 + 5.0)
    assert lb.worker_state("w1") is ACTIVE
    assert lb.dispatch(task("t2")).worker_id == "w1"


def test_custom_cooldown(make_lb, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    w1.in_flight = w1.capacity
    lb = make_lb(w1, w2, overload_cooldown_s=1.0)
    lb.dispatch(task("t1"))
    clock.set(T0 + 1.0)
    assert lb.worker_state("w1") is ACTIVE


def test_dead_worker_fails_over_and_stays_unreachable(make_lb, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    w2.kill()
    lb = make_lb(w1, w2, w3)
    results = [lb.dispatch(task(f"t{i}")) for i in range(4)]
    assert [(r.worker_id, r.attempts) for r in results] == [("w1", 1), ("w3", 2), ("w1", 1), ("w3", 1)]
    assert lb.worker_state("w2") is UNREACHABLE
    w2.revive()  # nothing has told the balancer it is back
    assert served_by(lb, 2, "u") == ["w1", "w3"]
    assert lb.worker_state("w2") is UNREACHABLE


def test_crash_mid_task_fails_over(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    w1.crash_on_next()
    lb = make_lb(w1, w2)
    result = lb.dispatch(task("t1"))
    assert (result.worker_id, result.attempts) == ("w2", 2)
    assert lb.worker_state("w1") is UNREACHABLE
    assert w2.completed == [{"id": "t1"}]


def test_slow_worker_times_out_using_task_timeout(make_lb, make_workers, clock):
    (slow,) = make_workers("w1", latency_s=10.0)
    (fast,) = make_workers("w2")
    lb = make_lb(slow, fast, task_timeout_s=0.5)
    result = lb.dispatch(task("t1"))
    assert (result.worker_id, result.attempts) == ("w2", 2)
    assert clock.time() == T0 + 0.5
    assert lb.worker_state("w1") is UNREACHABLE


def test_silent_worker_times_out_after_default_timeout(make_lb, make_workers, clock):
    w1, w2 = make_workers("w1", "w2")
    w1.go_silent()
    lb = make_lb(w1, w2)
    assert lb.dispatch(task("t1")).worker_id == "w2"
    assert clock.time() == T0 + 2.0
    assert lb.worker_state("w1") is UNREACHABLE


def test_task_failure_raises_and_worker_stays_active(make_lb, make_workers):
    w1, w2, w3 = make_workers("w1", "w2", "w3")
    lb = make_lb(w1, w2, w3)
    bad = task("bad", poison=True)
    with pytest.raises(TaskFailed) as info:
        lb.dispatch(bad)
    assert (info.value.task_id, info.value.worker_id) == ("bad", "w1")
    assert bad.attempts == 1
    assert w2.received == [] and w3.received == []
    assert lb.worker_state("w1") is ACTIVE
    assert served_by(lb, 3) == ["w2", "w3", "w1"]


def test_no_workers_registered(make_lb):
    with pytest.raises(NoWorkersAvailable) as info:
        make_lb().dispatch(task("t1"))
    assert info.value.task_id == "t1"


def test_every_worker_tried_once_then_no_workers(make_lb, make_workers, clock):
    workers = make_workers("w1", "w2", "w3")
    for w in workers:
        w.go_silent()
    lb = make_lb(*workers)
    t1 = task("t1")
    with pytest.raises(NoWorkersAvailable):
        lb.dispatch(t1)
    assert t1.attempts == 3
    assert clock.time() == T0 + 6.0  # three timeouts of 2 s: each worker exactly once
    assert all(lb.worker_state(w.worker_id) is UNREACHABLE for w in workers)
    t2 = task("t2")
    with pytest.raises(NoWorkersAvailable):
        lb.dispatch(t2)
    assert t2.attempts == 0 and clock.time() == T0 + 6.0


def test_attempts_accumulate_on_the_task(make_lb, make_workers):
    w1, w2 = make_workers("w1", "w2")
    w1.kill()
    lb = make_lb(w1, w2)
    t = task("t1")
    assert lb.dispatch(t).attempts == 2 and t.attempts == 2
    assert lb.dispatch(t).attempts == 3 and t.attempts == 3
