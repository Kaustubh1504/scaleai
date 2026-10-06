from dataclasses import dataclass, field


@dataclass
class Backend:
    id: str
    pool: str
    weight: int
    max_conns: int
    enabled: bool = True
    healthy: bool = True
    fails: int = 0
    active: list = field(default_factory=list)  # end times (ms) of open connections
    served: int = 0
    peak: int = 0
    busy_ms: int = 0


@dataclass(frozen=True)
class Request:
    request_id: str
    pool: str
    client_id: str
    arrival_ms: int
    duration_ms: int


@dataclass(frozen=True)
class Probe:
    backend_id: str
    at_ms: int
    healthy: bool
