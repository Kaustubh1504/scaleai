from dataclasses import dataclass
from enum import Enum


class BackendState(Enum):
    HEALTHY = "healthy"
    DOWN = "down"


@dataclass(frozen=True)
class Backend:
    id: str
    zone: str
    weight: int
    max_conns: int


@dataclass(frozen=True)
class Request:
    id: str
    t_ms: int
    session: str
    duration_ms: int


@dataclass(frozen=True)
class HealthCheck:
    t_ms: int
    backend: str
    ok: bool
