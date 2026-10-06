from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Robot:
    id: str
    camera_hz: float
    camera_offset_ms: int
    joint_offset_ms: int
    calibrated_at: datetime


@dataclass(frozen=True)
class Task:
    name: str
    min_s: float
    max_s: float
    required: tuple


@dataclass(frozen=True)
class Episode:
    id: str
    robot: str
    task: str
    operator: str
    started_at: datetime
    outcome: str


@dataclass
class Verdict:
    episode: Episode
    reason: str | None
    duration_s: float | None

    @property
    def valid(self):
        return self.reason is None
