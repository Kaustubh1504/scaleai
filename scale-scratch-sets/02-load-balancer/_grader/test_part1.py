"""Part 1: states and transitions, submit, dispatch, complete, idempotency."""

import pytest


def test_enums_and_values(m):
    assert [s.name for s in m.WorkerState] == ["IDLE", "BUSY", "DRAINING", "FAILED", "REMOVED"]
    assert [s.name for s in m.TaskState] == ["PENDING", "ASSIGNED", "COMPLETED", "EXPIRED", "DEAD"]
    assert all(s.value == s.name for s in m.WorkerState)
    assert all(s.value == s.name for s in m.TaskState)


def test_allowed_transitions_table(m):
    W = m.WorkerState
    assert m.ALLOWED_TRANSITIONS == {
        W.IDLE: {W.BUSY, W.DRAINING, W.FAILED},
        W.BUSY: {W.IDLE, W.DRAINING, W.FAILED},
        W.DRAINING: {W.REMOVED, W.FAILED},
        W.FAILED: {W.IDLE, W.REMOVED},
        W.REMOVED: set(),
    }


def test_invalid_transition_is_an_exception(m):
    assert issubclass(m.InvalidTransition, Exception)


def test_register_starts_idle(lb, m):
    lb.register_worker("w1")
    lb.register_worker("w2", capacity=3)
    assert lb.worker_state("w1") is m.WorkerState.IDLE
    assert lb.worker_state("w2") is m.WorkerState.IDLE


def test_register_duplicate_and_bad_capacity(lb):
    lb.register_worker("w1")
    with pytest.raises(ValueError):
        lb.register_worker("w1")
    with pytest.raises(ValueError):
        lb.register_worker("w2", capacity=0)
    with pytest.raises(ValueError):
        lb.register_worker("w3", capacity=-1)


def test_unknown_ids_raise_keyerror(lb):
    with pytest.raises(KeyError):
        lb.worker_state("nope")
    with pytest.raises(KeyError):
        lb.task_state("nope")


def test_submit_new_is_pending(lb, m):
    assert lb.submit("t1", 1) is True
    assert lb.task_state("t1") is m.TaskState.PENDING


def test_submit_is_idempotent_in_every_state(lb, m):
    lb.register_worker("w1")
    assert lb.submit("t1", 1) is True
    assert lb.submit("t1", 1) is False                      # PENDING
    lb.dispatch()
    assert lb.submit("t1", 9) is False                      # ASSIGNED
    assert lb.task_state("t1") is m.TaskState.ASSIGNED
    assert lb.complete("w1", "t1", 1) is True
    assert lb.submit("t1", 9) is False                      # COMPLETED
    assert lb.task_state("t1") is m.TaskState.COMPLETED
    assert lb.dispatch() == []


def test_duplicate_submit_does_not_change_priority(lb):
    lb.register_worker("w1")
    lb.submit("low", 1)
    lb.submit("high", 5)
    assert lb.submit("low", 100) is False
    assert lb.dispatch() == [("high", "w1", 1)]


def test_dispatch_highest_priority_first(lb):
    lb.register_worker("w1", capacity=3)
    lb.submit("a", 1)
    lb.submit("b", 7)
    lb.submit("c", 3)
    assert [t for t, _, _ in lb.dispatch()] == ["b", "c", "a"]


def test_priority_ties_are_fifo(lb):
    lb.register_worker("w1", capacity=10)
    for i in range(6):
        lb.submit(f"t{i}", 2)
    lb.submit("neg", -1)
    lb.submit("top", 3)
    assert [t for t, _, _ in lb.dispatch()] == ["top", "t0", "t1", "t2", "t3", "t4", "t5", "neg"]


def test_least_loaded_worker_with_capacity(lb):
    lb.register_worker("big", capacity=3)
    lb.register_worker("small", capacity=1)
    for i in range(5):
        lb.submit(f"t{i}", 1)
    # big(0) small(0) -> big; big(1) small(0) -> small; small full -> big, big
    assert lb.dispatch() == [("t0", "big", 1), ("t1", "small", 1), ("t2", "big", 1), ("t3", "big", 1)]
    assert lb.dispatch() == []


def test_least_loaded_ties_by_registration_order(lb):
    lb.register_worker("z", capacity=2)
    lb.register_worker("a", capacity=2)
    lb.register_worker("m", capacity=2)
    for i in range(6):
        lb.submit(f"t{i}", 1)
    assert [w for _, w, _ in lb.dispatch()] == ["z", "a", "m", "z", "a", "m"]


def test_least_loaded_counts_in_flight_not_ratio(lb):
    lb.register_worker("w1", capacity=10)
    lb.register_worker("w2", capacity=2)
    lb.submit("x", 1)
    lb.submit("y", 1)
    assert lb.dispatch() == [("x", "w1", 1), ("y", "w2", 1)]
    lb.complete("w1", "x", 1)
    lb.submit("z", 1)
    assert lb.dispatch() == [("z", "w1", 1)]  # w1 has 0 in flight, w2 has 1


def test_dispatch_stops_when_no_worker_and_leaves_pending(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 2)
    lb.submit("b", 1)
    assert lb.dispatch() == [("a", "w1", 1)]
    assert lb.task_state("b") is m.TaskState.PENDING
    assert lb.dispatch() == []


def test_dispatch_with_no_workers_or_no_tasks(lb):
    assert lb.dispatch() == []
    lb.submit("a", 1)
    assert lb.dispatch() == []
    lb.register_worker("w1")
    assert lb.dispatch() == [("a", "w1", 1)]
    assert lb.dispatch() == []


def test_busy_idle_bookkeeping(lb, m):
    lb.register_worker("w1", capacity=2)
    lb.submit("a", 1)
    lb.submit("b", 1)
    lb.dispatch()
    assert lb.worker_state("w1") is m.WorkerState.BUSY
    lb.complete("w1", "a", 1)
    assert lb.worker_state("w1") is m.WorkerState.BUSY
    lb.complete("w1", "b", 1)
    assert lb.worker_state("w1") is m.WorkerState.IDLE


def test_complete_frees_slot(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.submit("b", 1)
    assert lb.dispatch() == [("a", "w1", 1)]
    assert lb.complete("w1", "a", 1) is True
    assert lb.task_state("a") is m.TaskState.COMPLETED
    assert lb.dispatch() == [("b", "w1", 1)]


def test_complete_mismatches_return_false_and_change_nothing(lb, m):
    lb.register_worker("w1")
    lb.register_worker("w2")
    lb.submit("a", 1)
    lb.dispatch()
    assert lb.complete("w2", "a", 1) is False       # wrong worker
    assert lb.complete("w1", "a", 2) is False       # wrong attempt
    assert lb.complete("w1", "zzz", 1) is False     # unknown task
    assert lb.complete("ghost", "a", 1) is False    # unknown worker
    assert lb.task_state("a") is m.TaskState.ASSIGNED
    assert lb.worker_state("w1") is m.WorkerState.BUSY
    assert lb.complete("w1", "a", 1) is True
    assert lb.complete("w1", "a", 1) is False       # already completed


def test_dynamic_registration(lb):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.submit("b", 1)
    assert lb.dispatch() == [("a", "w1", 1)]
    lb.register_worker("w2")
    assert lb.dispatch() == [("b", "w2", 1)]
