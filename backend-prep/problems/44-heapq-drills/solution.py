"""44. heapq drills: reference solution."""

from __future__ import annotations

import heapq
import itertools
from typing import Iterable, Iterator


def top_k(scores: Iterable[tuple[str, float]], k: int) -> list[tuple[str, float]]:
    return heapq.nsmallest(k, scores, key=lambda s: (-s[1], s[0])) if k > 0 else []


def merge_logs(*streams: Iterable[dict]) -> Iterator[dict]:
    return heapq.merge(*streams, key=lambda rec: rec["ts"])  # lazy and stable


class TaskScheduler:
    def __init__(self) -> None:
        self.heap = []
        self.seq = itertools.count()

    def submit(self, task_id: str, priority: int, payload: dict | None = None) -> None:
        # seq gives FIFO within a priority and stops the tuple compare reaching payload
        heapq.heappush(self.heap, (-priority, next(self.seq), task_id, payload))

    def pop(self) -> tuple[str, dict | None]:
        return heapq.heappop(self.heap)[2:]  # IndexError when empty

    def __len__(self) -> int:
        return len(self.heap)


if __name__ == "__main__":
    print(top_k([("a1", 0.9), ("a2", 0.95), ("a3", 0.9)], 2))
    a = [{"ts": 1, "shard": "a"}, {"ts": 3, "shard": "a"}]
    b = [{"ts": 1, "shard": "b"}, {"ts": 2, "shard": "b"}]
    print([(r["ts"], r["shard"]) for r in merge_logs(a, b)])
    s = TaskScheduler()
    s.submit("t_b", 1, {"x": 1})
    s.submit("t_a", 1, {"x": 2})
    s.submit("t_z", 5)
    print([s.pop() for _ in range(len(s))])
