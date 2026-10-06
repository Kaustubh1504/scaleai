from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Session:
    session_id: str
    room: str
    capacity: int


@dataclass
class Member:
    member_id: str
    name: str
    tier: str


@dataclass
class Hold:
    hold_id: str
    session_id: str
    member_id: str
    seats: int
    placed_at: datetime
    confirmed_at: datetime | None = None


@dataclass
class SessionResult:
    session_id: str
    booked: list = field(default_factory=list)
    waitlist: list = field(default_factory=list)
    seats_booked: int = 0
