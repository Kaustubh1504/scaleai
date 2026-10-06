from dataclasses import dataclass, field
from enum import Enum


class Status(Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class Item:
    item_id: str
    category: str
    answer: str
    weight: float


@dataclass(frozen=True)
class Attempt:
    model: str
    item_id: str
    attempt: int
    status: Status
    output: str


@dataclass
class ModelScore:
    model: str
    correct: list = field(default_factory=list)
    unparsed: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    earned: float = 0.0
    possible: float = 0.0
