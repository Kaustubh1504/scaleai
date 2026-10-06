from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Session:
    id: str
    title: str
    capacity: int
    starts_at: datetime


@dataclass(frozen=True)
class Event:
    id: str
    at: datetime
    action: str
    session_id: str
    attendee: str
    seats: int


@dataclass
class Hold:
    attendee: str
    seats: int
    held_at: datetime


@dataclass
class Booking:
    session_id: str
    attendee: str
    seats: int
    status: str  # confirmed, comped or cancelled
