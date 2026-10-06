"""Domain objects shared by the registry and the balancer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class WorkerState(str, Enum):
    """How the balancer currently sees a worker (not the worker's own idea of itself)."""

    ACTIVE = "active"  # eligible for new tasks
    OVERLOADED = "overloaded"  # reachable but at capacity; skip it for now
    UNREACHABLE = "unreachable"  # not responding; skip it until it proves it is alive


@dataclass
class Task:
    id: str
    priority: int = 0  # higher runs first
    payload: Any = None  # handed to the worker unchanged
    attempts: int = 0  # how many workers this task has been sent to, over its lifetime


@dataclass(frozen=True)
class DispatchResult:
    task_id: str
    worker_id: str
    result: Any  # whatever worker.process() returned
    attempts: int  # task.attempts after the dispatch


class Worker(Protocol):
    """What the balancer needs from a worker. ``mock_services.workers.MockWorker`` implements it."""

    worker_id: str

    def process(self, payload: Any, timeout: float | None = None) -> Any: ...

    def heartbeat(self) -> dict | None: ...
