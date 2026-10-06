from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Team:
    team_id: str
    name: str
    disqualified: bool


@dataclass(frozen=True)
class Submission:
    submission_id: str
    team_id: str
    submitted_at: datetime
    correct: int
    total: int
    accepted: bool


@dataclass(frozen=True)
class TeamStats:
    team_id: str
    best_score: float
    best_at: datetime
    accepted: int
