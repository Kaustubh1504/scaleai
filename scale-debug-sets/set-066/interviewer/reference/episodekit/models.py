from dataclasses import dataclass
from datetime import datetime


@dataclass
class Robot:
    robot_id: str
    rate_hz: float
    active: bool = True


@dataclass
class Episode:
    episode_id: str
    robot_id: str
    task: str
    operator: str
    recorded_at: datetime


@dataclass
class Stream:
    episode_id: str
    sensor: str
    timestamps_ms: list


@dataclass
class EpisodeResult:
    episode_id: str
    task: str
    recorded_at: datetime
    valid: bool
    reason: str | None
    duration_ms: int
    sync_ratio: float | None = None
