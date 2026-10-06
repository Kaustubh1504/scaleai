"""Deliver platform events to webhook subscribers.

Status: first cut. ``dispatch_due()`` POSTs every event to every subscription
that wants its type. It does not look at the response and remembers nothing
between calls, so every call sends everything again.

Keep the constructor signature and the ``dispatch_due`` / ``delivery`` methods:
the interviewer's tests build a Dispatcher with their own state directory,
HTTP client and clock.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from mock_services.clock import Clock

from .events import EventStore
from .subscriptions import Subscription

log = logging.getLogger(__name__)


@dataclass
class DispatchReport:
    """What one ``dispatch_due()`` call did."""

    attempted: int = 0
    delivered: int = 0
    failed: int = 0
    dead: int = 0
    skipped_lines: list[int] = field(default_factory=list)


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
    ):
        """
        state_dir:     directory this dispatcher owns (created if missing)
        events:        the platform's event log
        subscriptions: who receives what
        http:          the client used for every webhook request
        clock:         time source; use clock.time(), never the time module
        max_attempts / timeout_s: retry and request-timeout settings (not used yet)
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.events = events
        self.subscriptions = list(subscriptions)
        self.http = http
        self.clock = clock
        self.max_attempts = max_attempts
        self.timeout_s = timeout_s

    def dispatch_due(self) -> DispatchReport:
        """Process every delivery that is due now."""
        report = DispatchReport()
        for event in self.events.read():
            for sub in self.subscriptions:
                if not sub.wants(event.type):
                    continue
                report.attempted += 1
                try:
                    self.http.post(sub.url, json=event.to_dict())
                except httpx.HTTPError as exc:
                    log.warning("delivery of %s to %s failed: %s", event.id, sub.id, exc)
        return report

    def delivery(self, event_id: str, subscription_id: str) -> dict:
        """The current state of one delivery (see PART1.md)."""
        raise NotImplementedError("delivery state is not tracked yet")
