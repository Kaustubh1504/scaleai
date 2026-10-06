from dataclasses import dataclass
from datetime import date


class Contributor:
    """One row of contributors.csv plus the running state of a staffing pass."""

    projects = []

    def __init__(self, cid, name, locale, weekly_hours, rating, active, joined):
        self.id = cid
        self.name = name
        self.locale = locale
        self.rating = rating
        self.active = active
        self.joined = joined
        self.hours_left = weekly_hours
        self.courses = {}

    def __repr__(self):
        return f"Contributor({self.id!r}, rating={self.rating}, hours_left={self.hours_left})"


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    priority: int
    seats: int
    hours_per_seat: float
    locale: str
    courses: tuple


@dataclass(frozen=True)
class CourseResult:
    contributor_id: str
    course: str
    result: str
    taken_on: date
