import itertools

import pytest


def test_group_unsorted_input(sol):
    """group_by_project handles unsorted input (sort before groupby)"""
    tasks = [{"id": "t1", "project": "b"}, {"id": "t2", "project": "a"},
             {"id": "t3", "project": "b"}, {"id": "t4", "project": "a"}, {"id": "t5", "project": "c"}]
    got = sol.group_by_project(tasks)
    assert got == {"a": ["t2", "t4"], "b": ["t1", "t3"], "c": ["t5"]}, \
        "groupby on unsorted data splits a project into several groups and the dict keeps only the last"
    assert list(got) == ["a", "b", "c"], "keys must be in ascending project order"


def test_group_empty_and_generator(sol):
    """group_by_project works on a generator and on empty input"""
    assert sol.group_by_project(iter([])) == {}
    gen = ({"id": f"t{i}", "project": "p"} for i in range(3))
    assert sol.group_by_project(gen) == {"p": ["t0", "t1", "t2"]}


def test_batched_basic(sol):
    """batched yields lists of n with a shorter last batch"""
    assert list(sol.batched(range(7), 3)) == [[0, 1, 2], [3, 4, 5], [6]]
    assert list(sol.batched([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]], "no empty trailing batch"
    assert list(sol.batched([], 5)) == []


def test_batched_lazy_infinite(sol):
    """batched is lazy: works on an endless generator and reads at most n items ahead"""
    consumed = []

    def endless():
        for i in itertools.count():
            consumed.append(i)
            yield i

    gen = sol.batched(endless(), 3)
    assert next(gen) == [0, 1, 2]
    assert next(gen) == [3, 4, 5]
    assert len(consumed) <= 6, f"read {len(consumed)} items to produce 2 batches of 3"


def test_batched_bad_n(sol):
    """batched with n < 1 raises ValueError"""
    with pytest.raises(ValueError):
        list(sol.batched([1, 2], 0))


def test_flatten_one_level(sol):
    """flatten_once flattens exactly one level and accepts generators of iterables"""
    assert sol.flatten_once([[1, [2]], [3], []]) == [1, [2], 3]
    assert sol.flatten_once(iter([(1, 2), range(3, 5)])) == [1, 2, 3, 4]


def test_deltas(sol):
    """deltas returns consecutive differences; fewer than 2 values gives []"""
    assert sol.deltas([10, 13, 13, 20]) == [3, 0, 7]
    assert sol.deltas([5]) == [] and sol.deltas([]) == []
    assert sol.deltas(iter([1, 4, 2])) == [3, -2], "must work on a one-shot iterator"


def test_running_totals(sol):
    """running_totals returns cumulative sums of the same length"""
    assert sol.running_totals([3, 1, 4]) == [3, 4, 8]
    assert sol.running_totals([]) == []
    assert sol.running_totals(iter([2, -2, 5])) == [2, 0, 5]
