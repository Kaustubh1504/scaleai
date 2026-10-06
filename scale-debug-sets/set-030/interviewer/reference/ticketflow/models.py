import copy
from dataclasses import dataclass
from datetime import datetime

TICKET_DEFAULTS = {"state": "new", "labels": [], "first_response": None, "updated_at": None}


@dataclass
class Ticket:
    ticket_id: str
    severity: int
    vip: bool
    opened_at: datetime
    state: str
    labels: list
    first_response: datetime | None
    updated_at: datetime | None


def new_ticket(ticket_id, severity, vip, opened_at):
    fields = copy.deepcopy(TICKET_DEFAULTS)
    return Ticket(ticket_id=ticket_id, severity=severity, vip=vip, opened_at=opened_at, **fields)


@dataclass(frozen=True)
class Event:
    seq: int
    ts: datetime
    ticket_id: str
    actor: str
    action: str
    value: str


@dataclass(frozen=True)
class Transition:
    source: str
    action: str
    target: str
    roles: frozenset
    counts_as_response: bool
