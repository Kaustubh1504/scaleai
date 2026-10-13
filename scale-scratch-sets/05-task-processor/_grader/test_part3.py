"""Part 3: update_deadline with lazy deletion, plus a randomized oracle check."""

import random

import pytest
from conftest import drain, time_limit


def test_spec_example_3(tp):
    tp.add_task("x", 10)
    tp.add_task("y", 20)
    tp.add_task("z", 30, ["x"])
    tp.add_task("w", 20)
    tp.update_deadline("w", 5)
    tp.update_deadline("y", 5)
    tp.update_deadline("z", 1)
    assert [tp.consume_task() for _ in range(5)] == ["y", "w", "x", "z", None]
    with pytest.raises(KeyError):
        tp.update_deadline("x", 0)
    with pytest.raises(KeyError):
        tp.update_deadline("nope", 1)


def test_update_earlier(tp):
    tp.add_task("a", 1)
    tp.add_task("b", 5)
    tp.update_deadline("b", 0)
    assert drain(tp) == ["b", "a"]


def test_update_later(tp):
    tp.add_task("a", 1)
    tp.add_task("b", 5)
    tp.update_deadline("a", 10)
    assert drain(tp) == ["b", "a"]  # a's stale entry at 1 must be skipped, and a returned once


def test_update_later_no_duplicates(tp):
    tp.add_task("a", 1)
    tp.update_deadline("a", 3)
    tp.update_deadline("a", 2)
    assert tp.consume_task() == "a"
    assert tp.consume_task() is None
    assert len(tp) == 0


def test_repeated_updates_last_wins(tp):
    tp.add_task("a", 5)
    tp.add_task("b", 6)
    tp.add_task("c", 7)
    for d in [1, 100, 3, 50, 8]:
        tp.update_deadline("a", d)
    assert drain(tp) == ["b", "c", "a"]


def test_update_back_to_original_value(tp):
    tp.add_task("a", 5)
    tp.add_task("b", 4)
    tp.update_deadline("a", 1)
    tp.update_deadline("a", 5)
    assert drain(tp) == ["b", "a"]


def test_update_to_same_value(tp):
    tp.add_task("a", 5)
    tp.update_deadline("a", 5)
    tp.update_deadline("a", 5)
    assert drain(tp) == ["a"]


def test_update_not_ready_task(tp):
    tp.add_task("parent", 100, ["s"])
    tp.add_task("s", 1)
    tp.add_task("other", 50)
    tp.update_deadline("parent", 0)  # not ready yet: allowed, takes effect when it becomes ready
    assert tp.consume_task() == "s"
    assert tp.consume_task() == "parent"
    assert tp.consume_task() == "other"


def test_update_not_ready_task_later(tp):
    tp.add_task("parent", 0, ["s"])
    tp.add_task("s", 1)
    tp.add_task("other", 50)
    tp.update_deadline("parent", 99)
    assert drain(tp) == ["s", "other", "parent"]


def test_update_task_in_cycle_is_allowed(tp):
    tp.add_task("a", 1, ["b"])
    tp.add_task("b", 1, ["a"])
    tp.update_deadline("a", 0)  # pending, so no KeyError
    assert tp.consume_task() is None


def test_update_unknown_raises_keyerror(tp):
    with pytest.raises(KeyError):
        tp.update_deadline("ghost", 1)
    tp.add_task("p", 1, ["never-added"])
    with pytest.raises(KeyError):
        tp.update_deadline("never-added", 1)  # only referenced as a subtask; not a task


def test_update_consumed_raises_keyerror(tp):
    tp.add_task("a", 1)
    tp.add_task("b", 2)
    assert tp.consume_task() == "a"
    with pytest.raises(KeyError):
        tp.update_deadline("a", 0)
    assert drain(tp) == ["b"]  # the failed update didn't resurrect a


def test_update_does_not_change_len(tp):
    tp.add_task("a", 1)
    tp.add_task("b", 2, ["a"])
    tp.update_deadline("a", 9)
    tp.update_deadline("b", 0)
    assert len(tp) == 2


def test_tie_after_update_uses_original_add_order(tp):
    tp.add_task("first", 5)
    tp.add_task("second", 3)
    tp.update_deadline("second", 5)  # now tied with "first"; "first" was added earlier
    assert drain(tp) == ["first", "second"]


def test_tie_after_update_original_order_not_update_order(tp):
    tp.add_task("a", 9)
    tp.add_task("b", 9)
    tp.add_task("c", 9)
    tp.update_deadline("c", 1)
    tp.update_deadline("b", 1)
    tp.update_deadline("a", 1)  # updated last, but added first
    assert drain(tp) == ["a", "b", "c"]


def test_tie_after_update_on_not_ready_task(tp):
    tp.add_task("parent", 9, ["s"])  # added before "x"
    tp.add_task("s", 0)
    tp.add_task("x", 2)
    tp.update_deadline("parent", 2)
    assert drain(tp) == ["s", "parent", "x"]


def test_perf_50k_updates_on_one_task(TP):
    n = 100_000
    p = TP()
    with time_limit(what="100k adds + 50k update_deadline + drain"):
        for i in range(n):
            p.add_task(f"t{i}", i)
        for k in range(50_000):
            p.update_deadline("t0", n + k)  # always pushes t0 to the back
        out = [p.consume_task() for _ in range(n)]
    assert out == [f"t{i}" for i in range(1, n)] + ["t0"]
    assert p.consume_task() is None


def test_perf_random_updates(TP):
    rng = random.Random(11)
    n = 100_000
    p = TP()
    final = list(range(n))
    with time_limit(what="100k adds + 100k random update_deadline + drain"):
        for i in range(n):
            p.add_task(f"t{i}", i)
        for _ in range(100_000):
            i = rng.randrange(n)
            d = rng.randrange(n)
            final[i] = d
            p.update_deadline(f"t{i}", d)
        out = [p.consume_task() for _ in range(n)]
    assert out == [f"t{i}" for i in sorted(range(n), key=lambda i: (final[i], i))]


# ---------------------------------------------------------------------------
# Randomized comparison against a brute-force oracle.
# ---------------------------------------------------------------------------


class Oracle:
    """Obviously-correct O(n) implementation of the SPEC."""

    def __init__(self):
        self.pending = {}  # id -> [deadline, add_seq, set(subtasks)]
        self.consumed = set()
        self.seq = 0

    def add_task(self, tid, deadline, subtasks=None):
        if tid in self.pending or tid in self.consumed:
            raise ValueError(tid)
        self.pending[tid] = [deadline, self.seq, set(subtasks or ())]
        self.seq += 1

    def consume_task(self):
        ready = [(d, s, t) for t, (d, s, subs) in self.pending.items() if subs <= self.consumed]
        if not ready:
            return None
        _, _, t = min(ready)
        del self.pending[t]
        self.consumed.add(t)
        return t

    def update_deadline(self, tid, deadline):
        if tid not in self.pending:
            raise KeyError(tid)
        self.pending[tid][0] = deadline

    def __len__(self):
        return len(self.pending)


def _call(obj, name, *args):
    try:
        return ("ok", getattr(obj, name)(*args))
    except (ValueError, KeyError) as e:
        return ("raise", type(e).__name__)


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_random_against_oracle(TP, seed):
    rng = random.Random(seed)
    pool = [f"id{i}" for i in range(400)]
    p, o = TP(), Oracle()
    log = []
    for step in range(3000):
        r = rng.random()
        if r < 0.40:
            tid = rng.choice(pool)
            d = rng.choice([rng.randrange(10), rng.randrange(10) + 0.5, -rng.randrange(3)])
            k = rng.choice([0, 0, 0, 1, 1, 2, 3])
            subs = [rng.choice(pool) for _ in range(k)]  # may repeat, include tid itself, or never be added
            arg = subs if subs else rng.choice([[], None])
            op = ("add_task", tid, d, arg)
        elif r < 0.75:
            op = ("consume_task",)
        else:
            op = ("update_deadline", rng.choice(pool), rng.randrange(10))
        log.append(op)
        got, want = _call(p, *op), _call(o, *op)
        assert got == want, f"seed={seed} step={step} op={op}: got {got}, expected {want}\nlast ops: {log[-15:]}"
        assert len(p) == len(o), f"seed={seed} step={step}: len {len(p)} != {len(o)}"
    # drain at the end too
    while True:
        got, want = p.consume_task(), o.consume_task()
        assert got == want, f"seed={seed} final drain: got {got!r}, expected {want!r}"
        if want is None:
            break
