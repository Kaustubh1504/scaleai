from dataclasses import dataclass, field
from datetime import date


@dataclass
class Contributor:
    id: str
    name: str
    skills: set[str] = field(default_factory=set)
    completed_courses: set[str] = field(default_factory=set)
    rating: float = 0.0
    joined: date | None = None
    available: bool = True


@dataclass
class Project:
    id: str
    name: str
    priority: int
    headcount: int
    required_skill: str
    required_course: str | None = None
