"""Parse and validate ticket files (CSV and JSONL)."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

FIELDS = ("ticket_id", "customer_email", "subject", "body", "created_at")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# A parsed record, or None plus a reason when the row's structure is broken.
Row = tuple[dict | None, str | None]


class IngestError(ValueError):
    """The file as a whole is unusable."""


@dataclass
class IngestResult:
    total_rows: int = 0
    tickets: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _decode(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestError("file is not valid UTF-8") from exc
    if not text.strip():
        raise IngestError("file is empty")
    return text


def _csv_rows(text: str) -> Iterator[Row]:
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next((row for row in reader if row), None)
    if header is None:
        raise IngestError("file has no header row")
    names = [name.strip() for name in header]
    missing = [f for f in FIELDS if f not in names]
    if missing:
        raise IngestError(f"header is missing required columns: {', '.join(missing)}")
    for values in reader:
        if not values:  # blank line
            continue
        if len(values) != len(names):
            yield None, f"expected {len(names)} values, got {len(values)}"
        else:
            yield dict(zip(names, values)), None


def _jsonl_rows(text: str) -> Iterator[Row]:
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            yield None, "line is not valid JSON"
            continue
        if isinstance(record, dict):
            yield record, None
        else:
            yield None, "line is not a JSON object"


PARSERS = {".csv": _csv_rows, ".jsonl": _jsonl_rows}


def _valid_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _check(ticket: dict, seen_ids: set[str]) -> tuple[str, str] | None:
    """Return (field, message) for the first failing rule, or None if valid."""
    if not ticket["ticket_id"]:
        return "ticket_id", "ticket_id is required"
    if ticket["ticket_id"] in seen_ids:
        return "ticket_id", f"duplicate ticket_id {ticket['ticket_id']!r}"
    if not EMAIL_RE.match(ticket["customer_email"]):
        return "customer_email", "customer_email is not a valid email address"
    for name in ("subject", "body"):
        if not ticket[name]:
            return name, f"{name} is required"
    if not _valid_timestamp(ticket["created_at"]):
        return "created_at", "created_at is not an ISO-8601 timestamp"
    return None


def ingest(suffix: str, raw: bytes) -> IngestResult:
    rows = PARSERS[suffix](_decode(raw))
    result = IngestResult()
    seen_ids: set[str] = set()
    for row_number, (record, structural_error) in enumerate(rows, start=1):
        result.total_rows = row_number
        if record is None:
            result.errors.append({"row": row_number, "field": None, "message": structural_error})
            continue
        # Non-string values (JSONL) are treated as missing.
        ticket = {f: record[f].strip() if isinstance(record.get(f), str) else "" for f in FIELDS}
        problem = _check(ticket, seen_ids)
        if problem:
            result.errors.append({"row": row_number, "field": problem[0], "message": problem[1]})
        else:
            seen_ids.add(ticket["ticket_id"])
            result.tickets.append(ticket)
    return result
