from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Speaker:
    id: str
    accent: str
    held_out: bool


@dataclass(frozen=True)
class Clip:
    id: str
    speaker_id: str
    duration_ms: int
    transcript: str
    consent: bool
    recorded_on: date
