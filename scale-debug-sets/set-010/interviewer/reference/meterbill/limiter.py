from collections import defaultdict

WINDOW_MS = 60_000


def replay(requests, tenants):
    """Sliding-window limiter. Returns {request_id: retry_after_s} for throttled requests."""
    allowed = defaultdict(list)
    throttled = {}
    for req in sorted(requests, key=lambda r: (r.ts_ms, r.request_id)):
        limit = tenants[req.tenant].plan.rpm
        recent = [t for t in allowed[req.tenant] if req.ts_ms - t < WINDOW_MS]
        if len(recent) >= limit:
            oldest = min(recent)
            throttled[req.request_id] = (oldest + WINDOW_MS - req.ts_ms) / 1000
        else:
            allowed[req.tenant].append(req.ts_ms)
    return throttled
