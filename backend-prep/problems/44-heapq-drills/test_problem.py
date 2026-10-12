import itertools

import pytest


def test_top_k_order(sol):
    """top_k returns the k highest scores, highest first"""
    scores = [("a1", 0.5), ("a2", 0.9), ("a3", 0.7), ("a4", 0.1)]
    assert sol.top_k(scores, 2) == [("a2", 0.9), ("a3", 0.7)]


def test_top_k_ties(sol):
    """top_k breaks score ties by annotator id ascending"""
    scores = [("a9", 0.9), ("a3", 0.9), ("a5", 0.95), ("a1", 0.9)]
    assert sol.top_k(scores, 3) == [("a5", 0.95), ("a1", 0.9), ("a3", 0.9)], \
        "equal scores must be ordered by id ascending"


def test_top_k_edges(sol):
    """top_k with k <= 0 is [], k > n returns everything; accepts a generator"""
    assert sol.top_k([("a", 1.0)], 0) == []
    assert sol.top_k((s for s in [("b", 1.0), ("a", 2.0)]), 10) == [("a", 2.0), ("b", 1.0)]


def test_merge_logs_order_and_ties(sol):
    """merge_logs yields by ts; equal ts keep the order the streams were passed"""
    a = [{"ts": 1, "shard": "a"}, {"ts": 3, "shard": "a"}, {"ts": 3, "shard": "a2"}]
    b = [{"ts": 1, "shard": "b"}, {"ts": 2, "shard": "b"}, {"ts": 3, "shard": "b"}]
    got = [(r["ts"], r["shard"]) for r in sol.merge_logs(a, b)]
    assert got == [(1, "a"), (1, "b"), (2, "b"), (3, "a"), (3, "a2"), (3, "b")]


def test_merge_logs_lazy_infinite(sol):
    """merge_logs is lazy: works when one stream is an endless generator"""
    pulled = []

    def endless(shard):
        for i in itertools.count():
            pulled.append(shard)
            yield {"ts": i * 2.0, "shard": shard}

    finite = [{"ts": 1.0, "shard": "f"}, {"ts": 3.0, "shard": "f"}]
    first5 = list(itertools.islice(sol.merge_logs(endless("e"), finite), 5))
    assert [r["ts"] for r in first5] == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert len(pulled) <= 6, f"pulled {len(pulled)} records from the endless stream to produce 5 outputs"


def test_merge_logs_empty(sol):
    """merge_logs with no or empty streams yields nothing"""
    assert list(sol.merge_logs()) == []
    assert list(sol.merge_logs([], [])) == []


def test_scheduler_priority(sol):
    """TaskScheduler pops the highest priority first"""
    s = sol.TaskScheduler()
    s.submit("low", 1)
    s.submit("high", 10)
    s.submit("mid", 5)
    assert [s.pop()[0] for _ in range(3)] == ["high", "mid", "low"]


def test_scheduler_fifo_with_payloads(sol):
    """Equal priorities pop in submission order, even with dict payloads (no TypeError)"""
    s = sol.TaskScheduler()
    s.submit("t_c", 1, {"n": 1})
    s.submit("t_a", 1, {"n": 2})
    s.submit("t_b", 1, {"n": 3})
    assert len(s) == 3
    got = [s.pop() for _ in range(3)]
    assert got == [("t_c", {"n": 1}), ("t_a", {"n": 2}), ("t_b", {"n": 3})], \
        "ties must be FIFO, not by task id; use a counter as the second key"
    assert len(s) == 0


def test_scheduler_empty_pop(sol):
    """pop() on an empty TaskScheduler raises IndexError"""
    with pytest.raises(IndexError):
        sol.TaskScheduler().pop()
