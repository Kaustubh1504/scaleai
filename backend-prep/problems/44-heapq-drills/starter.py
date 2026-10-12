"""44. heapq drills

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import heapq
import itertools
from typing import Iterable, Iterator


def top_k(scores: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    raise NotImplementedError


def merge_logs(*streams: Iterable[dict]) -> Iterator[dict]:
    # heapq.merge is lazy and stable: equal keys come out in stream order.
    raise NotImplementedError


class TaskScheduler:
    def __init__(self) -> None:
        self._heap: list[tuple[int, int, str, dict | None]] = []
        self._seq = itertools.count()

    def submit(self, task_id: str, priority: int, payload: dict | None = None) -> None:
        # (-priority, seq): highest priority first, FIFO within a priority, never compares payloads.
        raise NotImplementedError

    def pop(self) -> tuple[str, dict | None]:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


if __name__ == "__main__":
    print(top_k([("a1", 0.9), ("a2", 0.95), ("a3", 0.9)], 2))
    a = [{"ts": 1, "shard": "a"}, {"ts": 3, "shard": "a"}]
    b = [{"ts": 1, "shard": "b"}, {"ts": 2, "shard": "b"}]
    print([(r["ts"], r["shard"]) for r in merge_logs(a, b)])
    s = TaskScheduler()
    s.submit("t_b", 1, {"x": 1}); s.submit("t_a", 1, {"x": 2}); s.submit("t_z", 5)
    print([s.pop() for _ in range(len(s))])
