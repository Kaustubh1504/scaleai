from dataclasses import dataclass
from datetime import datetime


class RowError(Exception):
    """Raised when a feed row cannot be accepted. `reason` is the reject code."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Category:
    code: str
    name: str
    active: bool


@dataclass
class Record:
    sku: str
    title: str
    category: str
    price_cents: int
    qty: int
    updated_at: datetime
    status: str
    source: str
    line: int

    @property
    def discontinued(self):
        return self.status == "discontinued"


@dataclass(frozen=True)
class Reject:
    source: str
    line: int
    reason: str
