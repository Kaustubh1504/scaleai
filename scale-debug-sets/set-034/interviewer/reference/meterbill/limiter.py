from .utils import age_seconds


class SlidingWindowLimiter:
    """Per-tenant sliding window over previously allowed requests."""

    def __init__(self, tenants):
        self.tenants = tenants
        self.history = {}

    def allow(self, tenant_id, ts):
        tenant = self.tenants[tenant_id]
        window = tenant.plan.window
        recent = [prev for prev in self.history.get(tenant_id, []) if age_seconds(ts, prev) < window]
        if len(recent) >= tenant.limit:
            return False
        recent.append(ts)
        self.history[tenant_id] = recent
        return True


def run(requests, tenants):
    """Return {request_id: allowed} processing requests in time order."""
    limiter = SlidingWindowLimiter(tenants)
    ordered = sorted(requests, key=lambda r: r.ts)
    return {req.request_id: limiter.allow(req.tenant_id, req.ts) for req in ordered}
