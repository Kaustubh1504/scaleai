# 31. Stay under an API's rate limit (client side)
# Standalone: copy this file as-is. Deps: stdlib

import threading
import time
from email.utils import parsedate_to_datetime


def make_rate_limiter(rate: float, burst: int = 1, clock=time.monotonic, sleep=time.sleep):
    """Returns acquire(): blocks until one more request is allowed (`rate` per second, bursts up to `burst`).
    Thread-safe: share one limiter across all workers hitting the same API."""
    state = {"tokens": float(burst), "last": clock()}
    lock = threading.Lock()

    def acquire():
        while True:
            with lock:
                now = clock()
                state["tokens"] = min(burst, state["tokens"] + (now - state["last"]) * rate)
                state["last"] = now
                if state["tokens"] >= 1:
                    state["tokens"] -= 1
                    return
                wait = (1 - state["tokens"]) / rate
            sleep(wait)

    return acquire


def retry_after_seconds(response, default: float = 1.0, cap: float = 60.0) -> float:
    """Seconds to wait from a Retry-After header (number of seconds or an HTTP date)."""
    value = response.headers.get("Retry-After")
    if not value:
        return default
    try:
        return min(cap, max(0.0, float(value)))
    except ValueError:
        pass
    try:
        return min(cap, max(0.0, parsedate_to_datetime(value).timestamp() - time.time()))
    except (TypeError, ValueError):
        return default
