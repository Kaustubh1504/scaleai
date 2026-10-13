"""Part 2: heartbeat timeout, task timeout, retries/DEAD, stale attempts, deadlines."""

import pytest


def test_heartbeat_unknown_raises_keyerror(lb):
    with pytest.raises(KeyError):
        lb.heartbeat("nope")


def test_heartbeat_timeout_is_strict(lb, clock, m):
    lb.register_worker("w1")
    clock.set(10)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.IDLE      # 10 - 0 is not > 10
    clock.set(10.5)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.FAILED


def test_heartbeat_keeps_worker_alive(lb, clock, m):
    lb.register_worker("w1")
    for t in (8, 16, 24):
        clock.set(t)
        lb.heartbeat("w1")
        lb.tick()
    clock.set(34)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.IDLE


def test_custom_heartbeat_timeout(make, clock, m):
    lb = make(heartbeat_timeout=2)
    lb.register_worker("w1")
    clock.set(2.5)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.FAILED


def test_heartbeat_failure_requeues_in_flight(lb, clock, m):
    lb.register_worker("w1", capacity=2)
    lb.submit("a", 1)
    lb.submit("b", 1)
    assert lb.dispatch() == [("a", "w1", 1), ("b", "w1", 1)]
    clock.set(11)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.FAILED
    assert lb.task_state("a") is m.TaskState.PENDING
    assert lb.task_state("b") is m.TaskState.PENDING
    assert lb.dispatch() == []                    # FAILED worker gets nothing
    lb.register_worker("w2", capacity=2)
    assert lb.dispatch() == [("a", "w2", 2), ("b", "w2", 2)]
    assert lb.complete("w1", "a", 1) is False     # old lease is dead


def test_heartbeat_recovers_failed_worker(lb, clock, m):
    lb.register_worker("w1")
    clock.set(11)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.FAILED
    lb.heartbeat("w1")
    assert lb.worker_state("w1") is m.WorkerState.IDLE
    lb.tick()                                     # last-seen was refreshed
    assert lb.worker_state("w1") is m.WorkerState.IDLE
    lb.submit("a", 1)
    assert lb.dispatch() == [("a", "w1", 1)]


def test_task_timeout_is_strict_and_frees_slot(lb, clock, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.submit("b", 1)
    clock.set(1)
    assert lb.dispatch() == [("a", "w1", 1)]
    for t in (9, 18, 27, 31):
        clock.set(t)
        lb.heartbeat("w1")
        lb.tick()
    assert lb.task_state("a") is m.TaskState.ASSIGNED  # 31 - 1 is not > 30
    clock.set(31.5)
    lb.tick()
    assert lb.task_state("a") is m.TaskState.PENDING
    assert lb.worker_state("w1") is m.WorkerState.IDLE
    # requeued "a" keeps its place ahead of "b"
    assert lb.dispatch() == [("a", "w1", 2)]


def test_stale_complete_after_timeout(make, clock, m):
    lb = make(task_timeout=5)
    lb.register_worker("w1")
    lb.register_worker("w2")
    lb.submit("a", 1)
    assert lb.dispatch() == [("a", "w1", 1)]
    clock.set(6)
    lb.tick()
    assert lb.dispatch() == [("a", "w1", 2)]      # w1 and w2 tie at 0 -> w1
    assert lb.complete("w1", "a", 1) is False     # stale attempt from same worker
    assert lb.task_state("a") is m.TaskState.ASSIGNED
    assert lb.complete("w1", "a", 2) is True


def test_stale_complete_from_old_worker_after_reassignment(make, clock, m):
    lb = make(task_timeout=5)
    lb.register_worker("w1")
    lb.register_worker("w2")
    lb.submit("a", 1)
    lb.submit("filler", 0)
    assert lb.dispatch() == [("a", "w1", 1), ("filler", "w2", 1)]
    lb.complete("w2", "filler", 1)
    clock.set(6)
    lb.tick()
    lb.submit("blocker", 9)
    assert lb.dispatch() == [("blocker", "w1", 1), ("a", "w2", 2)]
    assert lb.complete("w1", "a", 1) is False
    assert lb.fail("w1", "a", 1) is False
    assert lb.task_state("a") is m.TaskState.ASSIGNED
    assert lb.complete("w2", "a", 2) is True


def test_fail_requeues_with_next_attempt(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    assert lb.fail("w1", "a", 1) is True
    assert lb.task_state("a") is m.TaskState.PENDING
    assert lb.worker_state("w1") is m.WorkerState.IDLE
    assert lb.dispatch() == [("a", "w1", 2)]


def test_fail_mismatch_returns_false(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    assert lb.fail("w1", "a", 2) is False
    assert lb.fail("w2", "a", 1) is False
    assert lb.fail("w1", "zzz", 1) is False
    assert lb.task_state("a") is m.TaskState.ASSIGNED


def test_exactly_four_attempts_then_dead(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    attempts = []
    for _ in range(10):
        got = lb.dispatch()
        if not got:
            break
        (tid, wid, att), = got
        attempts.append(att)
        assert lb.fail(wid, tid, att) is True
    assert attempts == [1, 2, 3, 4]
    assert lb.task_state("a") is m.TaskState.DEAD
    assert lb.dead_letter() == ["a"]
    assert lb.submit("a", 1) is False


def test_max_retries_zero_means_one_attempt(make, m):
    lb = make(max_retries=0)
    lb.register_worker("w1")
    lb.submit("a", 1)
    assert lb.dispatch() == [("a", "w1", 1)]
    lb.fail("w1", "a", 1)
    assert lb.task_state("a") is m.TaskState.DEAD
    assert lb.dispatch() == []


def test_dead_letter_order_is_death_order(make):
    lb = make(max_retries=0)
    lb.register_worker("w1", capacity=3)
    for t in ("x", "y", "z"):
        lb.submit(t, 1)
    lb.dispatch()
    assert lb.dead_letter() == []
    lb.fail("w1", "z", 1)
    lb.fail("w1", "x", 1)
    lb.fail("w1", "y", 1)
    assert lb.dead_letter() == ["z", "x", "y"]


def test_timeouts_count_toward_retries(make, clock, m):
    lb = make(task_timeout=1, heartbeat_timeout=1000, max_retries=1)
    lb.register_worker("w1")
    lb.submit("a", 1)
    assert lb.dispatch() == [("a", "w1", 1)]
    clock.set(2)
    lb.tick()
    assert lb.dispatch() == [("a", "w1", 2)]
    clock.set(4)
    lb.tick()
    assert lb.task_state("a") is m.TaskState.DEAD
    assert lb.dead_letter() == ["a"]


def test_requeued_task_keeps_original_position(lb, m):
    lb.register_worker("w1")
    lb.submit("first", 5)
    assert lb.dispatch() == [("first", "w1", 1)]
    lb.submit("second", 5)
    lb.submit("third", 5)
    lb.fail("w1", "first", 1)
    assert lb.dispatch() == [("first", "w1", 2)]


def test_expired_task_is_never_dispatched(lb, clock, m):
    lb.submit("late", 9, deadline=5)
    lb.submit("ok", 1)
    clock.set(6)
    lb.register_worker("w1", capacity=2)
    assert lb.dispatch() == [("ok", "w1", 1)]
    assert lb.task_state("late") is m.TaskState.EXPIRED
    assert lb.submit("late", 9) is False


def test_deadline_is_strict(lb, clock, m):
    lb.register_worker("w1")
    lb.submit("a", 1, deadline=5)
    clock.set(5)
    lb.tick()
    assert lb.task_state("a") is m.TaskState.PENDING
    assert lb.dispatch() == [("a", "w1", 1)]


def test_tick_expires_pending_but_not_assigned(lb, clock, m):
    lb.register_worker("w1")
    lb.submit("run", 2, deadline=3)
    lb.submit("wait", 1, deadline=3)
    assert lb.dispatch() == [("run", "w1", 1)]
    clock.set(4)
    lb.tick()
    assert lb.task_state("wait") is m.TaskState.EXPIRED
    assert lb.task_state("run") is m.TaskState.ASSIGNED
    assert lb.complete("w1", "run", 1) is True


def test_requeued_task_past_deadline_expires(make, clock, m):
    lb = make(task_timeout=5)
    lb.register_worker("w1")
    lb.submit("a", 1, deadline=3)
    lb.dispatch()
    clock.set(6)
    lb.tick()                                     # timeout -> PENDING, then deadline -> EXPIRED
    assert lb.task_state("a") is m.TaskState.EXPIRED
    assert lb.dispatch() == []


def test_tick_does_not_dispatch(lb, m):
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.tick()
    assert lb.task_state("a") is m.TaskState.PENDING
    assert lb.worker_state("w1") is m.WorkerState.IDLE


def test_heartbeat_failure_runs_before_task_timeout(make, clock, m):
    # both rules match the same task at the same tick: it must count as ONE failed attempt
    lb = make(heartbeat_timeout=5, task_timeout=5, max_retries=1)
    lb.register_worker("w1")
    lb.submit("a", 1)
    lb.dispatch()
    clock.set(6)
    lb.tick()
    assert lb.worker_state("w1") is m.WorkerState.FAILED
    assert lb.task_state("a") is m.TaskState.PENDING
    lb.register_worker("w2")
    assert lb.dispatch() == [("a", "w2", 2)]


def test_heartbeat_failure_can_kill_task(make, clock, m):
    lb = make(max_retries=0)
    lb.register_worker("w1", capacity=2)
    lb.submit("a", 1)
    lb.submit("b", 1)
    lb.dispatch()
    clock.set(11)
    lb.tick()
    assert lb.dead_letter() == ["a", "b"]
