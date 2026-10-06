from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Seat:
    seat_id: str
    section: str
    price: float


@dataclass(frozen=True)
class Event:
    seq: int
    event_id: str
    at: datetime
    customer: str
    action: str
    seat_id: str


@dataclass
class Hold:
    customer: str
    held_at: datetime
