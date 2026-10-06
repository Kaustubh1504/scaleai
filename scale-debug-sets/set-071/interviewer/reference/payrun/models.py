from dataclasses import dataclass
from datetime import datetime


@dataclass
class Contributor:
    id: str
    name: str
    tier: str
    carryover: int
    active: bool


@dataclass
class Entry:
    entry_id: str
    contributor_id: str
    task_type: str
    units: int
    status: str
    completed_at: datetime


@dataclass
class Adjustment:
    contributor_id: str
    kind: str
    cents: int
    note: str


@dataclass
class Statement:
    contributor_id: str
    carryover: int = 0
    lines: int = 0
    earned: int = 0
    bonus: int = 0
    clawback: int = 0

    @property
    def gross(self):
        return self.earned + self.bonus - self.clawback + self.carryover
