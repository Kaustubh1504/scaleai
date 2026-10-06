from collections import deque
from datetime import timedelta

from .timeparse import chronological


class SlidingWindow:
    def __init__(self, limit, window_s):
        self.limit = limit
        self.window = timedelta(seconds=window_s)
        self.accepted = deque()

    def offer(self, ts):
        """Return (accepted, retry_after_s)."""
        cutoff = ts - self.window
        while self.accepted and self.accepted[0] < cutoff:
            self.accepted.popleft()
        if len(self.accepted) < self.limit:
            self.accepted.append(ts)
            return True, None
        elapsed = (ts - self.accepted[0]).seconds
        return False, round(self.window.total_seconds() - elapsed, 3)


def replay(requests, limits):
    """limits: tenant_id -> (limit, window_s). Returns (accepted, rejected, timeline)."""
    windows = {tid: SlidingWindow(*limit) for tid, limit in limits.items()}
    accepted, rejected, timeline = [], {}, {}
    for req in chronological(requests):
        timeline.setdefault(req.tenant_id, []).append(req.request_id)
        ok, retry_after = windows[req.tenant_id].offer(req.ts)
        if ok:
            accepted.append(req)
        else:
            rejected[req.request_id] = retry_after
    return accepted, rejected, timeline
