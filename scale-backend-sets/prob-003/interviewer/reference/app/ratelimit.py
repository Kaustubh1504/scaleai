"""Per-tenant token buckets driven by the injected clock."""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass

from app.config import Plan
from mock_services.clock import Clock

# Absorbs float noise such as 0.30000000000000004 tokens when rounding.
_EPS = 1e-9


@dataclass
class Decision:
    allowed: bool
    remaining: int  # whole tokens left after this request
    retry_after: int | None = None  # seconds, only when not allowed


class RateLimiter:
    def __init__(self, clock: Clock):
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, float]] = {}  # tenant -> (tokens, updated_at)

    def _refill(self, tenant_id: str, plan: Plan) -> float:
        now = self._clock.time()
        tokens, updated = self._buckets.get(tenant_id, (plan.burst, now))
        tokens = min(plan.burst, tokens + max(0.0, now - updated) * plan.refill_per_s)
        self._buckets[tenant_id] = (tokens, now)
        return tokens

    def remaining(self, tenant_id: str, plan: Plan) -> int:
        with self._lock:
            return math.floor(self._refill(tenant_id, plan) + _EPS)

    def try_acquire(self, tenant_id: str, plan: Plan) -> Decision:
        with self._lock:
            tokens = self._refill(tenant_id, plan)
            if tokens + _EPS >= 1:
                tokens = max(0.0, tokens - 1)
                self._buckets[tenant_id] = (tokens, self._clock.time())
                return Decision(True, math.floor(tokens + _EPS))
            wait = (1 - tokens) / plan.refill_per_s
            return Decision(False, math.floor(tokens + _EPS), max(1, math.ceil(wait - _EPS)))
