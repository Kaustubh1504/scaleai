from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Contributor:
    id: str
    name: str
    team: str
    status: str

    @property
    def banned(self):
        return self.status == "banned"


@dataclass(frozen=True)
class Submission:
    id: str
    contributor_id: str
    task_id: str
    points: int
    submitted_at: datetime


@dataclass
class Standing:
    contributor_id: str
    name: str
    score: int
    tasks_solved: int
    attempts: int
    rank: int = 0

    def as_dict(self):
        return {
            "rank": self.rank,
            "contributor_id": self.contributor_id,
            "name": self.name,
            "score": self.score,
            "tasks_solved": self.tasks_solved,
            "attempts": self.attempts,
        }
