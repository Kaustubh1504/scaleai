from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    OPEN = "open"
    PAUSED = "paused"


@dataclass(frozen=True)
class Contributor:
    id: str
    name: str
    weekly_hours: int
    rating: float


@dataclass(frozen=True)
class Project:
    id: str
    priority: int
    status: Status
    seats: int
    hours_per_seat: int
    required_courses: tuple


class CourseStats:
    """Coverage numbers for one course."""
    demand = 0

    def __init__(self, course_id):
        self.holders = set()
        self.course_id = course_id

    def as_dict(self):
        return {"holders": len(self.holders), "demand": self.demand}
