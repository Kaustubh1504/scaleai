"""Part 2: subtask dependencies."""

import pytest
from conftest import drain, time_limit


def test_spec_example_2(tp):
    tp.add_task("build", 1, ["fetch", "lint"])
    tp.add_task("lint", 3)
    tp.add_task("fetch", 2, ["auth"])
    tp.add_task("deploy", 0, ["build"])
    tp.add_task("auth", 9)
    assert len(tp) == 5
    assert [tp.consume_task() for _ in range(6)] == ["lint", "auth", "fetch", "build", "deploy", None]
    assert len(tp) == 0


def test_parent_waits_for_subtask(tp):
    tp.add_task("child", 10)
    tp.add_task("parent", 1, ["child"])
    assert tp.consume_task() == "child"  # parent has the earlier deadline but isn't ready
    assert tp.consume_task() == "parent"


def test_nothing_ready_returns_none_and_keeps_tasks(tp):
    tp.add_task("parent", 1, ["missing"])
    assert tp.consume_task() is None
    assert len(tp) == 1


def test_never_added_subtask_is_unmet_until_added_and_consumed(tp):
    tp.add_task("parent", 1, ["later"])
    assert tp.consume_task() is None
    tp.add_task("later", 5)
    assert tp.consume_task() == "later"
    assert tp.consume_task() == "parent"
    assert tp.consume_task() is None


def test_adding_subtask_alone_does_not_satisfy(tp):
    tp.add_task("parent", 1, ["s"])
    tp.add_task("s", 5, ["blocker"])  # s exists but can't be consumed yet
    assert tp.consume_task() is None
    tp.add_task("blocker", 9)
    assert drain(tp) == ["blocker", "s", "parent"]


def test_already_consumed_subtask_counts_as_met(tp):
    tp.add_task("s", 1)
    assert tp.consume_task() == "s"
    tp.add_task("parent", 5, ["s"])
    assert tp.consume_task() == "parent"


def test_partially_consumed_subtasks(tp):
    tp.add_task("s1", 1)
    tp.add_task("s2", 2)
    assert tp.consume_task() == "s1"
    tp.add_task("parent", 0, ["s1", "s2"])
    assert tp.consume_task() == "s2"
    assert tp.consume_task() == "parent"


def test_ready_parent_competes_by_deadline(tp):
    tp.add_task("s", 1)
    tp.add_task("parent", 2, ["s"])
    tp.add_task("other", 3)
    assert drain(tp) == ["s", "parent", "other"]


def test_ready_parent_ties_use_add_order(tp):
    tp.add_task("parent", 5, ["s"])  # added first
    tp.add_task("s", 0)
    tp.add_task("other", 5)  # same deadline, added after parent
    assert tp.consume_task() == "s"
    assert tp.consume_task() == "parent"
    assert tp.consume_task() == "other"


def test_diamond(tp):
    #      top
    #     /   \
    #  left   right
    #     \   /
    #     base
    tp.add_task("top", 0, ["left", "right"])
    tp.add_task("left", 4, ["base"])
    tp.add_task("right", 3, ["base"])
    tp.add_task("base", 10)
    tp.add_task("free", 7)
    assert drain(tp) == ["free", "base", "right", "left", "top"]


def test_multiple_parents_share_a_subtask(tp):
    tp.add_task("p1", 3, ["s"])
    tp.add_task("p2", 1, ["s"])
    tp.add_task("p3", 2, ["s", "q"])
    tp.add_task("s", 9)
    assert tp.consume_task() == "s"
    assert tp.consume_task() == "p2"
    assert tp.consume_task() == "p1"
    assert tp.consume_task() is None  # p3 still waits for q
    tp.add_task("q", 0)
    assert drain(tp) == ["q", "p3"]


def test_duplicate_ids_in_subtasks_count_once(tp):
    tp.add_task("parent", 1, ["s", "s", "s"])
    tp.add_task("s", 2)
    assert tp.consume_task() == "s"
    assert tp.consume_task() == "parent"


def test_cycle_never_ready_no_error(tp):
    tp.add_task("a", 1, ["b"])
    tp.add_task("b", 2, ["a"])
    tp.add_task("free", 3)
    assert tp.consume_task() == "free"
    assert tp.consume_task() is None
    assert tp.consume_task() is None
    assert len(tp) == 2


def test_self_dependency_never_ready(tp):
    tp.add_task("a", 1, ["a"])
    assert tp.consume_task() is None
    assert len(tp) == 1


def test_task_depending_on_cycle_never_ready(tp):
    tp.add_task("a", 1, ["b"])
    tp.add_task("b", 1, ["c"])
    tp.add_task("c", 1, ["a"])
    tp.add_task("d", 0, ["c", "e"])
    tp.add_task("e", 5)
    assert drain(tp) == ["e"]
    assert len(tp) == 4


def test_duplicate_id_validation_with_subtasks(tp):
    tp.add_task("parent", 1, ["s"])
    with pytest.raises(ValueError):
        tp.add_task("parent", 1)
    tp.add_task("s", 2)
    assert drain(tp) == ["s", "parent"]
    with pytest.raises(ValueError):
        tp.add_task("s", 1)


def test_len_counts_not_ready_tasks(tp):
    tp.add_task("p", 1, ["s"])
    tp.add_task("q", 1, ["never"])
    assert len(tp) == 2
    tp.add_task("s", 1)
    assert len(tp) == 3
    drain(tp)
    assert len(tp) == 1  # q is still pending


def test_perf_100k_chain_added_in_reverse(TP):
    n = 100_000
    p = TP()
    with time_limit(what="100k-long dependency chain"):
        # c{i} depends on c{i-1}; added from the end so every subtask is added after its parent.
        # Deadlines decrease along the chain, so the heap order fights the dependency order.
        for i in range(n - 1, 0, -1):
            p.add_task(f"c{i}", n - i, [f"c{i - 1}"])
        assert p.consume_task() is None
        p.add_task("c0", n)
        out = [p.consume_task() for _ in range(n)]
    assert out == [f"c{i}" for i in range(n)]
    assert p.consume_task() is None
    assert len(p) == 0


def test_perf_wide_fan_in(TP):
    n = 100_000
    p = TP()
    with time_limit(what="one task with 100k subtasks"):
        p.add_task("root", -1, [f"s{i}" for i in range(n)])
        for i in range(n):
            p.add_task(f"s{i}", i)
        out = [p.consume_task() for _ in range(n + 1)]
    assert out[-1] == "root"
    assert out[:3] == ["s0", "s1", "s2"]
    assert p.consume_task() is None
