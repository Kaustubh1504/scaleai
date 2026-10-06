"""The platform's append-only event log, stored as JSON Lines.

Each line is one event:

    {"id": "evt_...", "type": "task.completed", "created_at": "2024-06-01T10:00:00Z", "data": {...}}

Producers append with ``EventStore.append``; the dispatcher only reads. The file
may be appended to while the dispatcher runs, so every read starts from the top.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

REQUIRED_STRINGS = ("id", "type", "created_at")


class MalformedEvent(ValueError):
    """A line in the events file is not a valid event."""


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    created_at: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "created_at": self.created_at, "data": self.data}

    @classmethod
    def from_dict(cls, raw: Any) -> "Event":
        if not isinstance(raw, dict):
            raise MalformedEvent("event is not a JSON object")
        for key in REQUIRED_STRINGS:
            if not isinstance(raw.get(key), str) or not raw[key]:
                raise MalformedEvent(f"{key!r} must be a non-empty string")
        if not isinstance(raw.get("data"), dict):
            raise MalformedEvent("'data' must be a JSON object")
        return cls(raw["id"], raw["type"], raw["created_at"], raw["data"])


@dataclass
class ScanResult:
    events: list[Event] = field(default_factory=list)
    skipped_lines: list[int] = field(default_factory=list)


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:16]}"


class EventStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def append(self, event: Event) -> None:
        """Append one event (used by producers and tests)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def read(self) -> list[Event]:
        """Every valid event, in file order (see ``scan``)."""
        return self.scan().events

    def scan(self) -> ScanResult:
        """Read the whole file: valid events in file order plus the line numbers skipped.

        Blank lines are ignored. A line is skipped if it is not a valid event or
        repeats the id of an earlier valid event. A missing file means no events yet.
        """
        result = ScanResult()
        if not self.path.exists():
            return result
        seen: set[str] = set()
        with self.path.open(encoding="utf-8", errors="replace") as fh:
            for line_no, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    event = Event.from_dict(json.loads(line))
                    if event.id in seen:
                        raise MalformedEvent(f"duplicate event id {event.id!r}")
                except ValueError as exc:  # json.JSONDecodeError and MalformedEvent
                    log.warning("%s:%d: skipping malformed event: %s", self.path.name, line_no, exc)
                    result.skipped_lines.append(line_no)
                    continue
                seen.add(event.id)
                result.events.append(event)
        return result
