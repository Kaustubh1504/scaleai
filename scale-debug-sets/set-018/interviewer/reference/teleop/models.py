from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Robot:
    robot_id: str
    model: str
    max_gap_ms: int
    active: bool


@dataclass
class Episode:
    episode_id: str
    robot_id: str
    operator: str
    task: str
    recorded_on: date
    success: bool
    camera_ms: list[int] = field(default_factory=list)
    joints_ms: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class EpisodeMetrics:
    frames: int
    span_ms: int
    duration_s: float
    max_gap_ms: int
    sync_rate: float
