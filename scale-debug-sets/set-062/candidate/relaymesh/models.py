from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WorkerState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DRAINING = "draining"
    DOWN = "down"


ACCEPTING = (WorkerState.HEALTHY, WorkerState.DEGRADED)


@dataclass
class Worker:
    worker_id: str
    zone: str
    weight: float
    max_inflight: int
    state: WorkerState
    inflight: list = field(default_factory=list)  # end times (ms) of running requests


@dataclass
class Request:
    request_id: str
    zone: str
    arrival_ms: int
    duration_ms: int

    @property
    def end_ms(self) -> int:
        return self.arrival_ms + self.duration_ms


@dataclass
class HealthEvent:
    at_ms: int
    worker_id: str
    state: WorkerState
