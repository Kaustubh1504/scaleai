"""Per-worker health bookkeeping: state, overload cooldown and liveness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lb.models import WorkerState


def reports_overload(in_flight: int, capacity: int) -> bool:
    """A heartbeat at 80% of capacity or more means "overloaded" (integer maths, so 4/5 is exact)."""
    return in_flight * 5 >= capacity * 4


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parse_heartbeat(payload: Any) -> tuple[str, int, int] | None:
    """``(worker_id, in_flight, capacity)``, or None if the payload is malformed."""
    if not isinstance(payload, dict):
        return None
    worker_id, in_flight, capacity = payload.get("worker_id"), payload.get("in_flight"), payload.get("capacity")
    if not isinstance(worker_id, str) or not _is_int(in_flight) or not _is_int(capacity):
        return None
    if in_flight < 0 or capacity < 1:
        return None
    return worker_id, in_flight, capacity


@dataclass
class WorkerHealth:
    seq: int  # registration sequence number: defines the rotation order
    last_seen: float  # time of the last valid heartbeat, or of registration
    state: WorkerState = WorkerState.ACTIVE
    overloaded_until: float = 0.0
    in_flight: int | None = None  # load from the last heartbeat
    capacity: int | None = None

    def current(self, now: float) -> WorkerState:
        """The state at ``now``; an overload whose cooldown has passed reads as ACTIVE."""
        if self.state is WorkerState.OVERLOADED and now >= self.overloaded_until:
            self.state = WorkerState.ACTIVE
        return self.state

    def mark_overloaded(self, now: float, cooldown_s: float) -> None:
        self.state = WorkerState.OVERLOADED
        self.overloaded_until = now + cooldown_s

    def mark_unreachable(self) -> None:
        self.state = WorkerState.UNREACHABLE

    def is_stale(self, now: float, timeout_s: float) -> bool:
        return now - self.last_seen > timeout_s

    def record_heartbeat(self, now: float, in_flight: int, capacity: int, cooldown_s: float) -> None:
        self.last_seen, self.in_flight, self.capacity = now, in_flight, capacity
        if reports_overload(in_flight, capacity):
            self.mark_overloaded(now, cooldown_s)
        else:
            self.state = WorkerState.ACTIVE
