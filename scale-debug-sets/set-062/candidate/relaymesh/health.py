"""Apply health-check transitions as the replay clock advances."""
from __future__ import annotations


class HealthFeed:
    def __init__(self, events, workers):
        self.events = list(events)
        self.by_id = {w.worker_id: w for w in workers}
        self.pos = 0

    # VERIFIED
    def apply_due(self, now_ms: int) -> None:
        while self.pos < len(self.events) and self.events[self.pos].at_ms <= now_ms:
            event = self.events[self.pos]
            worker = self.by_id.get(event.worker_id)
            if worker is not None:
                worker.state = event.state
            self.pos += 1

    def flush(self) -> None:
        self.apply_due(float("inf"))
