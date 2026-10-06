from collections import deque

from .models import Plan

WINDOW_S = 60


def limit_for(tenant, plans):
    """Requests allowed per sliding minute, or None for no limit."""
    if tenant.rpm_override is not None:
        return tenant.rpm_override
    if tenant.plan is Plan.ENTERPRISE:
        return None
    return plans[tenant.plan].rpm


def apply_limit(events, limit):
    """Split one tenant's events (any order) into (allowed, throttled), both by time."""
    allowed, throttled = [], []
    window = deque()
    for ev in sorted(events, key=lambda e: e.ts):
        while window and (ev.ts - window[0]).total_seconds() >= WINDOW_S:
            window.popleft()
        if limit is None or len(window) < limit:
            allowed.append(ev)
            window.append(ev.ts)
        else:
            throttled.append(ev)
    return allowed, throttled
