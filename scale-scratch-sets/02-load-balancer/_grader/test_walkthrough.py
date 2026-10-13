"""Replays the SPEC.md timeline walkthrough step by step, with the exact values printed there."""

import pytest


def test_spec_walkthrough(make, clock, m):
    W, T = m.WorkerState, m.TaskState
    lb = make(heartbeat_timeout=10, task_timeout=15, max_retries=2, scale_cooldown=20)

    # 1. t=0
    clock.set(0)
    assert lb.register_worker("w1", capacity=2) is None
    assert lb.register_worker("w2", capacity=1) is None
    # 2.
    assert lb.submit("a", 1, deadline=5) is True
    assert lb.submit("b", 5) is True
    assert lb.submit("c", 5) is True
    assert lb.submit("d", 3) is True
    assert lb.submit("b", 9) is False
    # 3. t=1
    clock.set(1)
    assert lb.dispatch() == [("b", "w1", 1), ("c", "w2", 1), ("d", "w1", 1)]
    assert lb.worker_state("w1") is W.BUSY and lb.worker_state("w2") is W.BUSY
    # 4. t=2
    clock.set(2)
    assert lb.complete("w2", "c", 1) is True
    assert lb.worker_state("w2") is W.IDLE
    # 5. t=6
    clock.set(6)
    assert lb.dispatch() == []
    assert lb.task_state("a") is T.EXPIRED
    # 6. t=8
    clock.set(8)
    assert lb.heartbeat("w1") is None
    assert lb.heartbeat("w2") is None
    # 7. t=16
    clock.set(16)
    assert lb.tick() is None
    assert lb.task_state("b") is T.ASSIGNED and lb.task_state("d") is T.ASSIGNED
    # 8. t=17
    clock.set(17)
    assert lb.tick() is None
    assert lb.task_state("b") is T.PENDING and lb.task_state("d") is T.PENDING
    assert lb.worker_state("w1") is W.IDLE
    assert lb.complete("w1", "b", 1) is False
    # 9. t=18
    clock.set(18)
    assert lb.heartbeat("w1") is None
    assert lb.dispatch() == [("b", "w1", 2), ("d", "w2", 2)]
    # 10. t=19
    clock.set(19)
    assert lb.tick() is None
    assert lb.worker_state("w2") is W.FAILED
    assert lb.task_state("d") is T.PENDING
    # 11. t=20
    clock.set(20)
    assert lb.dispatch() == [("d", "w1", 3)]
    # 12. t=21
    clock.set(21)
    assert lb.heartbeat("w2") is None
    assert lb.worker_state("w2") is W.IDLE
    # 13. t=22
    clock.set(22)
    assert lb.drain_worker("w1") is None
    assert lb.worker_state("w1") is W.DRAINING
    assert lb.submit("e", 2) is True
    assert lb.submit("f", 2) is True
    assert lb.submit("g", 2) is True
    assert lb.scaling_decision() == 1
    # 14. t=23
    clock.set(23)
    assert lb.complete("w1", "b", 2) is True
    assert lb.worker_state("w1") is W.DRAINING
    assert lb.dispatch() == [("e", "w2", 1)]
    # 15. t=24
    clock.set(24)
    assert lb.fail("w1", "d", 3) is True
    assert lb.task_state("d") is T.DEAD
    assert lb.dead_letter() == ["d"]
    assert lb.worker_state("w1") is W.REMOVED
    with pytest.raises(m.InvalidTransition):
        lb.heartbeat("w1")
    # 16. t=25
    clock.set(25)
    assert lb.scaling_decision() == 0
    # 17. t=30
    clock.set(30)
    assert lb.complete("w2", "e", 1) is True
    assert lb.register_worker("w3", capacity=3) is None
    # 18. t=31
    clock.set(31)
    assert lb.dispatch() == [("f", "w2", 1), ("g", "w3", 1)]
    # 19. t=32
    clock.set(32)
    assert lb.complete("w2", "f", 1) is True
    # 20. t=42
    clock.set(42)
    assert lb.scaling_decision() == 0
    # 21. t=43
    clock.set(43)
    assert lb.complete("w3", "g", 1) is True
    assert lb.scaling_decision() == -1
    # 22. t=44
    clock.set(44)
    assert lb.scaling_decision() == 0
