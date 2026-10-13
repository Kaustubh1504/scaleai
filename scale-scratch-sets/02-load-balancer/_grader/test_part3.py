"""Part 3: draining and scaling_decision with cooldown."""

import pytest


def test_drain_idle_worker_is_removed_immediately(lb, m):
    lb.register_worker("w1")
    lb.drain_worker("w1")
    assert lb.worker_state("w1") is m.WorkerState.REMOVED
    with pytest.raises(ValueError):
        lb.register_worker("w1")                  # ids are never reused


def test_drain_unknown_raises_keyerror(lb):
    with pytest.raises(KeyError):
        lb.drain_worker("nope")


def test_drain_busy_lifecycle_via_complete(lb, m):
    lb.register_worker("w1", capacity=2)
    lb.submit("a", 1)
    lb.submit("b", 1)
    lb.dispatch()
    lb.drain_worker("w1")
    assert lb.worker_state("w1") is m.WorkerState.DRAINING
    lb.submit("c", 1)
    assert lb.dispatch() == []                     # draining gets no new work
    assert lb.complete("w1", "a", 1) is True
    assert lb.worker_state("w1") is m.WorkerState.DRAINING
    assert lb.complete("w1", "b", 1) is True
    assert lb.worker_state("w1") is m.WorkerState.REMOVED
    assert lb.dispatch() == []


def test_drain_lifecycle_via_fail(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    lb.drain_worker("w1")
    assert lb.fail("w1", "a", 1) is True
    assert lb.worker_state("w1") is m.WorkerState.REMOVED
    assert lb.task_state("a") is m.TaskState.PENDING
    lb.register_worker("w2")
    assert lb.dispatch() == [("a", "w2", 2)]


def test_drain_lifecycle_via_task_timeout(make, clock, m):
    lb = make(task_timeout=5)
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    lb.drain_worker("w1")
    clock.set(6)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.REMOVED
    assert lb.task_state("a") is m.TaskState.PENDING


def test_draining_worker_heartbeats_and_can_fail(lb, clock, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    lb.drain_worker("w1")
    clock.set(8)
    lb.heartbeat("w1")
    assert lb.worker_state("w1") is m.WorkerState.DRAINING
    clock.set(18)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.DRAINING
    clock.set(18.5)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.FAILED
    assert lb.task_state("a") is m.TaskState.PENDING


def test_drain_failed_worker_goes_straight_to_removed(lb, clock, m):
    lb.register_worker("w1")
    clock.set(11)
    lb.tick()
    lb.drain_worker("w1")
    assert lb.worker_state("w1") is m.WorkerState.REMOVED


def test_illegal_transitions_via_public_api(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    lb.drain_worker("w1")
    with pytest.raises(m.InvalidTransition):
        lb.drain_worker("w1")                     # DRAINING -> DRAINING
    assert lb.worker_state("w1") is m.WorkerState.DRAINING
    lb.complete("w1", "a", 1)
    assert lb.worker_state("w1") is m.WorkerState.REMOVED
    with pytest.raises(m.InvalidTransition):
        lb.drain_worker("w1")                     # REMOVED -> DRAINING
    with pytest.raises(m.InvalidTransition):
        lb.heartbeat("w1")                        # REMOVED -> anything
    assert lb.worker_state("w1") is m.WorkerState.REMOVED


def test_removed_worker_is_never_failed_by_tick(lb, clock, m):
    lb.register_worker("w1")
    lb.drain_worker("w1")
    clock.set(100)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.REMOVED


def _load(lb, workers, pending, busy=0):
    for wid, cap in workers:
        lb.register_worker(wid, capacity=cap)
    for i in range(busy):
        lb.submit(f"busy{i}", 100)
    assert len(lb.dispatch()) == busy
    for i in range(pending):
        lb.submit(f"p{i}", 1)


def test_scale_up_threshold_is_strict(make):
    lb = make()
    _load(lb, [("w1", 2)], pending=4)              # 4 == 2*cap -> no
    assert lb.scaling_decision() == 0
    lb = make()
    _load(lb, [("w1", 2)], pending=5)
    assert lb.scaling_decision() == 1


def test_scale_up_with_zero_capacity(lb):
    assert lb.scaling_decision() == 0             # nothing pending, no workers
    lb.submit("a", 1)
    assert lb.scaling_decision() == 1


def test_scale_down_threshold_is_strict(make):
    lb = make()
    _load(lb, [("w1", 2), ("w2", 2)], pending=0, busy=1)   # util 1/4 == 0.25 -> no
    assert lb.scaling_decision() == 0
    lb = make()
    _load(lb, [("w1", 3), ("w2", 2)], pending=0, busy=1)   # util 1/5 < 0.25
    assert lb.scaling_decision() == -1


def test_no_scale_down_with_one_worker(lb):
    lb.register_worker("w1", capacity=10)
    assert lb.scaling_decision() == 0


def test_draining_and_failed_workers_not_counted(make, clock):
    lb = make()
    _load(lb, [("w1", 1), ("w2", 1)], pending=0, busy=2)
    lb.drain_worker("w2")
    for i in range(3):
        lb.submit(f"p{i}", 1)
    assert lb.scaling_decision() == 1             # cap=1 (w1 only): 3 > 2
    lb = make()
    lb.register_worker("w1")
    lb.register_worker("w2")
    lb.register_worker("w3")
    clock.set(5)
    lb.heartbeat("w1")
    clock.set(11)
    lb.tick()                                     # w2, w3 FAILED; eligible = [w1]
    assert lb.scaling_decision() == 0


def test_cooldown_after_nonzero(make, clock):
    lb = make()
    lb.submit("a", 1)
    clock.set(100)
    assert lb.scaling_decision() == 1
    clock.set(129.9)
    assert lb.scaling_decision() == 0
    clock.set(130)
    assert lb.scaling_decision() == 1             # now - t == cooldown: allowed again
    clock.set(131)
    assert lb.scaling_decision() == 0


def test_zero_decision_does_not_start_cooldown(make, clock):
    lb = make(scale_cooldown=5)
    clock.set(1)
    assert lb.scaling_decision() == 0
    lb.submit("a", 1)
    clock.set(2)
    assert lb.scaling_decision() == 1
    clock.set(6.9)
    assert lb.scaling_decision() == 0
    clock.set(7)
    assert lb.scaling_decision() == 1


def test_cooldown_applies_across_directions(make, clock):
    lb = make(scale_cooldown=10)
    lb.submit("a", 1)
    assert lb.scaling_decision() == 1
    lb.register_worker("w1")
    lb.register_worker("w2", capacity=4)
    lb.dispatch()                                 # a -> w1; util 1/5
    clock.set(9)
    assert lb.scaling_decision() == 0
    clock.set(10)
    assert lb.scaling_decision() == -1
