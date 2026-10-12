"""45. itertools drills: reference solution."""

from __future__ import annotations

from itertools import accumulate, chain, groupby, islice, pairwise
from operator import itemgetter
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")


def group_by_project(tasks: Iterable[dict]) -> dict[str, list[str]]:
    key = itemgetter("project")
    # groupby only merges adjacent keys; sorted is stable so ids keep input order
    groups = groupby(sorted(tasks, key=key), key=key)
    return {project: [t["id"] for t in grp] for project, grp in groups}


def batched(iterable: Iterable[T], n: int) -> Iterator[list[T]]:
    if n < 1:
        raise ValueError("n must be >= 1")
    it = iter(iterable)
    while chunk := list(islice(it, n)):
        yield chunk


def flatten_once(nested: Iterable[Iterable[T]]) -> list[T]:
    return list(chain.from_iterable(nested))


def deltas(values: Iterable[float]) -> list[float]:
    return [b - a for a, b in pairwise(values)]


def running_totals(values: Iterable[float]) -> list[float]:
    return list(accumulate(values))


if __name__ == "__main__":
    tasks = [{"id": "t1", "project": "b"}, {"id": "t2", "project": "a"},
             {"id": "t3", "project": "b"}]
    print(group_by_project(tasks))
    print(list(batched(range(7), 3)))
    print(flatten_once([[1, [2]], [3]]))
    print(deltas([10, 13, 13, 20]), running_totals([3, 1, 4]))
