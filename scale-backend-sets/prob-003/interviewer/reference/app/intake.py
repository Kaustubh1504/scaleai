"""The POST /tasks decision: idempotency, then rate limit, then create."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import Plan
from app.models import TaskIn
from app.ratelimit import RateLimiter
from app.store import KeyTaken, Store
from mock_services.clock import Clock

IDEMPOTENCY_TTL_S = 24 * 60 * 60


@dataclass
class Outcome:
    status: int
    body: dict
    replayed: bool = False
    remaining: int | None = None
    retry_after: int | None = None


class Intake:
    def __init__(self, store: Store, limiter: RateLimiter, clock: Clock):
        self._store, self._limiter, self._clock = store, limiter, clock
        # Serializes check-then-create within this process so concurrent retries replay
        # instead of colliding; the store's primary key covers other processes.
        self._lock = threading.Lock()

    def _existing(self, tenant_id: str, plan: Plan, key: str, fingerprint: str, now: float) -> Outcome | None:
        """Replay or 409 if a live record holds this key; None if the key is free."""
        record = self._store.get_record(tenant_id, key)
        if record is None or now >= record.created_at + IDEMPOTENCY_TTL_S:
            return None
        if record.fingerprint != fingerprint:
            return Outcome(409, {"detail": "Idempotency-Key was already used with a different body"})
        return Outcome(record.status, record.response, replayed=True,
                       remaining=self._limiter.remaining(tenant_id, plan))

    def create(self, tenant_id: str, plan: Plan, key: str | None, task: TaskIn) -> Outcome:
        fingerprint = task.fingerprint()
        with self._lock:
            now = self._clock.time()
            if key is not None and (existing := self._existing(tenant_id, plan, key, fingerprint, now)):
                return existing
            decision = self._limiter.try_acquire(tenant_id, plan)
            if not decision.allowed:
                return Outcome(429, {"detail": "rate limit exceeded", "retry_after": decision.retry_after},
                               remaining=decision.remaining, retry_after=decision.retry_after)
            doc = {
                "id": uuid.uuid4().hex,
                "tenant_id": tenant_id,
                **task.model_dump(),
                "created_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            }
            try:
                self._store.create_task(doc, key, fingerprint, now, expired_before=now - IDEMPOTENCY_TTL_S)
            except KeyTaken:
                # Another instance won the race between our read and our write.
                return self._existing(tenant_id, plan, key, fingerprint, now) or Outcome(
                    409, {"detail": "a request with this key is in progress"})
            return Outcome(201, doc, remaining=decision.remaining)
