from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class RawRow:
    source: str
    row: int
    fields: dict


@dataclass
class Record:
    email: str
    name: str
    country: str
    skills: list
    hours: int
    updated_at: datetime
    source: str
    priority: int


@dataclass
class Contributor:
    email: str
    name: str
    country: str
    hours: int
    updated_at: datetime
    skills: list = field(default_factory=list)
    sources: list = field(default_factory=list)
