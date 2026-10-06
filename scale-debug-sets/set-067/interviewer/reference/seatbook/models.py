from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Seat:
    section: str
    row: str
    number: int
    tier: str
    status: str = "available"
    holder: str | None = None

    @property
    def label(self):
        return f"{self.section}-{self.row}{self.number}"


@dataclass
class Request:
    request_id: str
    ts: datetime
    action: str
    customer: str
    section: str
    quantity: int


@dataclass
class Hold:
    request_id: str
    customer: str
    held_at: datetime
    seats: list = field(default_factory=list)
