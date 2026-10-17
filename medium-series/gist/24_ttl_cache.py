# 24. TTL cache with request coalescing
# Standalone: copy this file as-is. Deps: stdlib

import threading
import time


def make_cached(fn, ttl: float = 60.0, cache_none: bool = False, clock=time.monotonic):
    """Returns (cached, stats). cached(key) -> fn(key), remembered for `ttl` seconds.
    Concurrent misses for the same key make ONE call; the others wait and share its result or error.
    Errors are never cached; None is cached only if cache_none."""
    entries = {}                                          # key -> (value, expires_at)
    inflight = {}                                         # key -> {"event", "value"/"error"}
    lock = threading.Lock()
    stats = {"hits": 0, "misses": 0, "calls": 0, "coalesced": 0}

    def cached(key):
        with lock:
            hit = entries.get(key)
            if hit is not None and hit[1] > clock():
                stats["hits"] += 1
                return hit[0]
            slot = inflight.get(key)
            leader = slot is None
            if leader:
                slot = inflight[key] = {"event": threading.Event()}
                stats["misses"] += 1
                stats["calls"] += 1
            else:
                stats["coalesced"] += 1
        if not leader:
            slot["event"].wait()
            if "error" in slot:
                raise slot["error"]
            return slot["value"]
        try:
            value = fn(key)
            slot["value"] = value
            with lock:
                if value is not None or cache_none:
                    entries[key] = (value, clock() + ttl)
            return value
        except Exception as e:
            slot["error"] = e
            raise
        finally:
            with lock:
                inflight.pop(key, None)
            slot["event"].set()

    return cached, stats
