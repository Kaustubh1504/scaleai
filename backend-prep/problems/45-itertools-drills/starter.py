"""45. itertools drills

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from itertools import accumulate, chain, groupby, islice, pairwise
from operator import itemgetter
from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")


def group_by_project(tasks: Iterable[dict]) -> dict[str, list[str]]:
    raise NotImplementedError


def batched(iterable: Iterable[T], n: int) -> Iterator[list[T]]:
    raise NotImplementedError


def flatten_once(nested: Iterable[Iterable[T]]) -> list[T]:
    raise NotImplementedError


def deltas(values: Iterable[float]) -> list[float]:
    raise NotImplementedError


def running_totals(values: Iterable[float]) -> list[float]:
    raise NotImplementedError


if __name__ == "__main__":
    tasks = [{"id": "t1", "project": "b"}, {"id": "t2", "project": "a"}, {"id": "t3", "project": "b"}]
    print(group_by_project(tasks))
    print(list(batched(range(7), 3)))
    print(flatten_once([[1, [2]], [3]]))
    print(deltas([10, 13, 13, 20]), running_totals([3, 1, 4]))
