# 52. Fake HTTP server: scripted replies, call counting, max concurrency
# Standalone: copy this file as-is. Deps: stdlib

from collections import deque


def chunks(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def bfs(start, neighbors, max_depth=None) -> list[tuple]:
    """neighbors(node) -> iterable. Returns [(node, depth)] in visit order; mark seen on enqueue."""
    queue, seen, order = deque([(start, 0)]), {start}, []
    while queue:
        node, depth = queue.popleft()
        order.append((node, depth))
        if max_depth is not None and depth >= max_depth:
            continue
        for nxt in neighbors(node):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, depth + 1))
    return order
