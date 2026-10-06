from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Episode:
    id: str
    robot: str
    operator: str
    task: str
    recorded_at: datetime
    tags: list = field(default_factory=list)
    success: bool = False


@dataclass
class EpisodeStats:
    episode_id: str
    frames: int
    duration_ms: int
    fps: float | None
    max_gap_ms: int | None
    sync_ratio: float | None
    valid: bool = False
    reason: str | None = None

    def as_dict(self):
        return {
            "valid": self.valid,
            "reason": self.reason,
            "frames": self.frames,
            "duration_s": round(self.duration_ms / 1000, 2),
            "fps": self.fps,
            "max_gap_ms": self.max_gap_ms,
            "sync_ratio": self.sync_ratio,
        }
