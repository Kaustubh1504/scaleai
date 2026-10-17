# 41. Rate limit per client (token bucket)
# Standalone: copy this file as-is. Deps: stdlib + fastapi

import math
import time

from fastapi.responses import JSONResponse


def add_rate_limit(app, rate: float = 5, burst: int = 10, key=None):
    """429 + Retry-After when a client exceeds `rate` req/s (bursts up to `burst`). Per process."""
    buckets: dict[str, tuple[float, float]] = {}
    key = key or (lambda req: req.headers.get("X-API-Key") or req.client.host)

    def allow(k: str) -> tuple[bool, float]:
        now = time.monotonic()
        tokens, last = buckets.get(k, (burst, now))
        tokens = min(burst, tokens + (now - last) * rate)
        if tokens < 1:
            buckets[k] = (tokens, now)
            return False, (1 - tokens) / rate
        buckets[k] = (tokens - 1, now)
        return True, 0.0

    @app.middleware("http")
    async def middleware(request, call_next):
        ok, wait = allow(key(request))
        if not ok:
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429,
                                headers={"Retry-After": str(math.ceil(wait))})
        return await call_next(request)

    return allow
