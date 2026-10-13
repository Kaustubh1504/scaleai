"""Part 1: add_task / consume_task by earliest deadline (no dependencies)."""

import pytest
from conftest import drain, time_limit


def test_spec_example_1(tp):
    tp.add_task("a", 5)
    tp.add_task("b", 2)
    tp.add_task("c", 5)
    tp.add_task("d", 1)
    assert [tp.consume_task() for _ in range(5)] == ["d", "b", "a", "c", None]


def test_empty_returns_none(tp):
    assert tp.consume_task() is None
    assert tp.consume_task() is None


def test_returns_none_after_drained(tp):
    tp.add_task("x", 1)
    assert tp.consume_task() == "x"
    assert tp.consume_task() is None


def test_earliest_deadline_first(tp):
    for tid, d in [("t3", 30), ("t1", 10), ("t4", 40), ("t2", 20)]:
        tp.add_task(tid, d)
    assert drain(tp) == ["t1", "t2", "t3", "t4"]


def test_float_and_negative_deadlines(tp):
    tp.add_task("a", 1.5)
    tp.add_task("b", -2)
    tp.add_task("c", 1.25)
    tp.add_task("d", 0)
    assert drain(tp) == ["b", "d", "c", "a"]


def test_ties_use_add_order(tp):
    # ids chosen so that alphabetical order is the opposite of add order
    for tid in ["z", "y", "x", "w"]:
        tp.add_task(tid, 7)
    assert drain(tp) == ["z", "y", "x", "w"]


def test_ties_mixed_with_other_deadlines(tp):
    tp.add_task("late-1", 9)
    tp.add_task("b", 3)
    tp.add_task("late-2", 9)
    tp.add_task("a", 3)
    tp.add_task("first", 1)
    assert drain(tp) == ["first", "b", "a", "late-1", "late-2"]


def test_interleaved_add_and_consume(tp):
    tp.add_task("a", 5)
    tp.add_task("b", 3)
    assert tp.consume_task() == "b"
    tp.add_task("c", 1)
    tp.add_task("d", 4)
    assert tp.consume_task() == "c"
    assert tp.consume_task() == "d"
    assert tp.consume_task() == "a"
    assert tp.consume_task() is None


def test_empty_subtasks_list_is_ready(tp):
    tp.add_task("a", 2, [])
    tp.add_task("b", 1, None)
    assert drain(tp) == ["b", "a"]


def test_duplicate_pending_raises_and_state_unchanged(tp):
    tp.add_task("a", 5)
    with pytest.raises(ValueError):
        tp.add_task("a", 1)
    assert len(tp) == 1
    # the original deadline still applies
    tp.add_task("b", 3)
    assert drain(tp) == ["b", "a"]


def test_duplicate_after_consume_raises(tp):
    tp.add_task("a", 5)
    assert tp.consume_task() == "a"
    with pytest.raises(ValueError):
        tp.add_task("a", 5)
    assert len(tp) == 0
    assert tp.consume_task() is None


def test_len(tp):
    assert len(tp) == 0
    tp.add_task("a", 1)
    tp.add_task("b", 2)
    tp.add_task("c", 3)
    assert len(tp) == 3
    tp.consume_task()
    assert len(tp) == 2
    drain(tp)
    assert len(tp) == 0
    tp.consume_task()  # consuming from empty doesn't go negative
    assert len(tp) == 0


def test_instances_are_independent(TP):
    p1, p2 = TP(), TP()
    p1.add_task("a", 1)
    p2.add_task("a", 1)  # no ValueError: separate processors
    assert p1.consume_task() == "a"
    assert len(p2) == 1


def test_perf_200k_add_then_consume(TP):
    import random

    rng = random.Random(5)
    n = 200_000
    deadlines = [rng.randrange(1000) for _ in range(n)]  # many ties
    p = TP()
    with time_limit(what="200k add_task + 200k consume_task"):
        for i, d in enumerate(deadlines):
            p.add_task(f"t{i}", d)
        out = [p.consume_task() for _ in range(n)]
    expected = [f"t{i}" for i in sorted(range(n), key=lambda i: (deadlines[i], i))]
    assert out == expected
    assert p.consume_task() is None
