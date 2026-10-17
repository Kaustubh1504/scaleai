# 48. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib

import heapq
from collections import defaultdict


def schedule(tasks: dict) -> list:
    """{id: {"deadline": int, "deps": [ids]}} -> run order: deps first, earliest deadline among ready.
    Raises ValueError on unknown deps or a cycle. O((V + E) log V)."""
    indegree = {t: 0 for t in tasks}
    children = defaultdict(list)
    for t, spec in tasks.items():
        for d in spec["deps"]:
            if d not in tasks:
                raise ValueError(f"{t} depends on unknown task {d}")
            children[d].append(t)
            indegree[t] += 1
    ready = [(tasks[t]["deadline"], t) for t in tasks if indegree[t] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        _, t = heapq.heappop(ready)
        order.append(t)
        for c in children[t]:
            indegree[c] -= 1
            if indegree[c] == 0:
                heapq.heappush(ready, (tasks[c]["deadline"], c))
    if len(order) != len(tasks):
        raise ValueError("cycle in dependencies")
    return order
