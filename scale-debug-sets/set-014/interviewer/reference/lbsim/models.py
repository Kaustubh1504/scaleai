from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class State(Enum):
    UP = "up"
    DOWN = "down"
    DRAINING = "draining"


class Worker:
    """A backend in the pool. `active` holds the end times of its open connections."""

    def __init__(self, worker_id, zone, weight, max_conns, state):
        self.served = []
        self.worker_id = worker_id
        self.zone = zone
        self.weight = weight
        self.max_conns = max_conns
        self.state = state
        self.active = []

    def __repr__(self):
        return f"Worker({self.worker_id!r}, {self.state.value})"


@dataclass(frozen=True)
class Probe:
    worker_id: str
    checked_at: datetime
    result: str
    latency_ms: int | None


@dataclass(frozen=True)
class Request:
    request_id: str
    zone: str
    arrived_at: datetime
    duration_ms: int
