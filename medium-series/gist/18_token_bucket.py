# 18. Token bucket per tenant (non-blocking, injectable clock)
# Standalone: copy this file as-is. Deps: stdlib

import math
import threading
import time


def make_bucket_store(clock=time.monotonic):
    """take(key, burst, refill_per_s, cost=1) -> (allowed, retry_after_s).
    Each key has its own bucket: starts full, refills continuously (fractional tokens count), never above burst.
    retry_after_s = seconds until `cost` tokens exist, rounded UP, at least 1 (0 when allowed). Thread-safe."""
    buckets: dict = {}
    lock = threading.Lock()

    def take(key, burst: float, refill_per_s: float, cost: float = 1.0):
        with lock:
            now = clock()
            tokens, last = buckets.get(key, (float(burst), now))
            tokens = min(float(burst), tokens + (now - last) * refill_per_s)
            if tokens >= cost:
                buckets[key] = (tokens - cost, now)
                return True, 0
            buckets[key] = (tokens, now)
            return False, max(1, math.ceil(round((cost - tokens) / refill_per_s, 9)))

    return take
