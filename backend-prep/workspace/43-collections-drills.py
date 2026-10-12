"""43. collections drills

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import Counter, OrderedDict, defaultdict, deque
from typing import Any, Iterable


def top_labels(labels: Iterable[str], n: int) -> list[tuple[str, int]]:
    cnt = Counter(labels)
    s = sorted(cnt.items(), key=lambda k:(-k[1],k[0]))
    return [(l,c) for l,c in s][:n]


def group_by_annotator(submissions: Iterable[dict]) -> dict[str, list[str]]:
    cnt = defaultdict(list)
    
    for obj in submissions:
        ann = obj["annotator_id"]
        tid = obj["task_id"]
        cnt[ann].append(tid)
        
    return dict(cnt)

class SlidingWindowCounter:
    def __init__(self, window_s: float):
        self.window_s = window_s
        self.events: deque[float] = deque()
    
    
    def record(self, ts: float) -> None:
        self.events.append(ts)

    def count(self, now: float) -> int:
        while self.events and self.events[0] <= now - self.window_s:
            self.events.popleft()
        
        return sum(ts<=now for ts in self.events)


class LRUCache:
    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        self.capacity = capacity
        self.data: OrderedDict[Any, Any] = OrderedDict()

    def get(self, key: Any, default: Any = None) -> Any:
        if key not in self.data:
            return default
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key: Any, value: Any) -> None:
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)

    def __len__(self) -> int:
        return len(self.data)


if __name__ == "__main__":
    print(top_labels(["dog", "cat", "dog", "cat", "bird"], 2))
    print(group_by_annotator([{"annotator_id": "a", "task_id": "t1"}, {"annotator_id": "a", "task_id": "t2"}]))
    c = SlidingWindowCounter(60)
    for ts in (0, 30, 61):
        c.record(ts)
    print(c.count(61))
    cache = LRUCache(2)
    cache.put("a", 1); cache.put("b", 2); cache.get("a"); cache.put("c", 3)
    print(cache.get("b"), cache.get("a"), cache.get("c"))
