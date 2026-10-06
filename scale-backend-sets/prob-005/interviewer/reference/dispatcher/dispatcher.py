"""Deliver platform events to webhook subscribers.

One delivery per (event, subscription that wants the event's type). Each
``dispatch_due()`` call attempts every pending delivery whose ``next_attempt_at``
has passed, at most once per call. Failed attempts are classified (policy.py),
then either rescheduled with backoff / Retry-After or dead-lettered.

Durability: after every attempt the audit line is appended and the full delivery
state is saved atomically (state.py), so a new Dispatcher over the same state_dir
resumes exactly. Guarantee: at-least-once. A crash between sending a request and
saving its result means that request is sent again after the restart.

Keep the constructor signature and the ``dispatch_due`` / ``delivery`` methods:
the interviewer's tests build a Dispatcher with their own state directory,
HTTP client and clock.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from mock_services.clock import Clock

from .events import Event, EventStore
from .policy import Backoff, parse_retry_after, retryable_error, retryable_status
from .signing import SIGNATURE_HEADER, sign
from .state import AuditLog, DeliveryStore
from .subscriptions import Subscription

log = logging.getLogger(__name__)

PENDING, DELIVERED, DEAD = "pending", "delivered", "dead"


@dataclass
class DispatchReport:
    """What one ``dispatch_due()`` call did."""

    attempted: int = 0
    delivered: int = 0
    failed: int = 0
    dead: int = 0
    skipped_lines: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class AttemptResult:
    retryable: bool | None  # None: delivered
    status_code: int | None = None
    error: str | None = None
    retry_after: float | None = None


def new_delivery(event_id: str, subscription_id: str, due_at: float) -> dict:
    return {"event_id": event_id, "subscription_id": subscription_id, "status": PENDING,
            "attempts": 0, "next_attempt_at": due_at, "last_error": None}


def encode_body(event: Event) -> bytes:
    return json.dumps(event.to_dict(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class Dispatcher:
    def __init__(
        self,
        state_dir: Path | str,
        events: EventStore,
        subscriptions: list[Subscription],
        http: httpx.Client,
        clock: Clock,
        max_attempts: int = 5,
        timeout_s: float = 5.0,
        rng: random.Random | None = None,
    ):
        """
        state_dir:     directory this dispatcher owns (created if missing)
        events:        the platform's event log
        subscriptions: who receives what
        http:          the client used for every webhook request
        clock:         time source; use clock.time(), never the time module
        max_attempts:  attempts per delivery before it is dead (>= 1)
        timeout_s:     per-request timeout
        rng:           randomness for backoff jitter (seed it in tests if needed)
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.events = events
        self.subscriptions = list(subscriptions)
        self.http = http
        self.clock = clock
        self.max_attempts = max_attempts
        self.timeout_s = timeout_s
        self.backoff = Backoff(rng or random.Random())
        self.audit = AuditLog(self.state_dir / "audit.jsonl")
        self.store = DeliveryStore(self.state_dir / "deliveries.json")
        self._deliveries = self.store.load()

    def delivery(self, event_id: str, subscription_id: str) -> dict:
        """The current state of one delivery. KeyError if there is no such delivery."""
        return dict(self._deliveries[(event_id, subscription_id)])

    def dispatch_due(self) -> DispatchReport:
        """Process every delivery that is due now."""
        now = self.clock.time()
        scan = self.events.scan()
        report = DispatchReport(skipped_lines=scan.skipped_lines)
        for event in scan.events:
            for sub in self.subscriptions:
                if not sub.wants(event.type):
                    continue
                state = self._deliveries.get((event.id, sub.id)) or new_delivery(event.id, sub.id, now)
                if state["status"] != PENDING or state["next_attempt_at"] > now:
                    continue
                outcome = self._attempt(event, sub, state)
                report.attempted += 1
                setattr(report, outcome, getattr(report, outcome) + 1)
        return report

    def _attempt(self, event: Event, sub: Subscription, state: dict) -> str:
        """Send once, then record the result. Returns the audit outcome."""
        now = self.clock.time()
        result = self._send(event, sub, now)
        attempts = state["attempts"] + 1
        if result.retryable is None:
            status, outcome, next_at = DELIVERED, "delivered", None
        elif result.retryable and attempts < self.max_attempts:
            delay = result.retry_after if result.retry_after is not None else self.backoff.delay(attempts)
            status, outcome, next_at = PENDING, "failed", now + delay
        else:
            status, outcome, next_at = DEAD, "dead", None
        if outcome != "delivered":
            log.warning("delivery %s -> %s attempt %d %s: %s", event.id, sub.id, attempts, outcome, result.error)
        # Audit first: it records what happened on the wire, even if saving the state fails.
        self.audit.append({"ts": now, "event_id": event.id, "subscription_id": sub.id, "attempt": attempts,
                           "outcome": outcome, "status_code": result.status_code, "error": result.error})
        self._deliveries[(event.id, sub.id)] = {**state, "status": status, "attempts": attempts,
                                                "next_attempt_at": next_at, "last_error": result.error}
        self.store.save(self._deliveries.values())
        return outcome

    def _send(self, event: Event, sub: Subscription, now: float) -> AttemptResult:
        """One HTTP request. httpx errors become results; anything else propagates (a crash)."""
        body = encode_body(event)
        headers = {"Content-Type": "application/json", "X-Event-Id": event.id,
                   SIGNATURE_HEADER: sign(sub.secret, body, int(now))}
        try:
            response = self.http.post(sub.url, content=body, headers=headers, timeout=self.timeout_s)
        except httpx.HTTPError as exc:
            return AttemptResult(retryable_error(exc), error=f"{type(exc).__name__}: {exc}")
        code = response.status_code
        if 200 <= code < 300:
            return AttemptResult(None, status_code=code)
        retry_after = parse_retry_after(response) if code == 429 else None
        return AttemptResult(retryable_status(code), code, f"HTTP {code}", retry_after)
