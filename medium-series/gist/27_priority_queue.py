# 27. Priority queue with updates and removals (lazy deletion)
# Standalone: copy this file as-is. Deps: stdlib

import heapq
import itertools


def pq_new() -> dict:
    return {"heap": [], "live": {}, "seq": itertools.count()}


def pq_push(pq: dict, item_id, priority, payload=None) -> None:
    """Add, or change the priority of an existing id. Lower priority value pops first; ties pop FIFO."""
    seq = next(pq["seq"])
    pq["live"][item_id] = (priority, seq, payload)
    heapq.heappush(pq["heap"], (priority, seq, item_id))


def pq_remove(pq: dict, item_id) -> bool:
    return pq["live"].pop(item_id, None) is not None


def pq_pop(pq: dict):
    """(item_id, priority, payload) of the smallest live entry, or None. Stale heap entries are skipped."""
    while pq["heap"]:
        priority, seq, item_id = heapq.heappop(pq["heap"])
        live = pq["live"].get(item_id)
        if live is not None and live[1] == seq:
            del pq["live"][item_id]
            return item_id, priority, live[2]
    return None


def pq_peek(pq: dict):
    while pq["heap"]:
        priority, seq, item_id = pq["heap"][0]
        live = pq["live"].get(item_id)
        if live is not None and live[1] == seq:
            return item_id, priority, live[2]
        heapq.heappop(pq["heap"])
    return None
