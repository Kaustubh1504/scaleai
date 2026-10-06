import csv
import json
from datetime import date, datetime
from decimal import Decimal

from .models import Adjustment, Contributor, Entry

TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%d %b %Y %H:%M")
ADJUSTMENT_KINDS = ("bonus", "clawback")


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def parse_bool(value):
    return clean(value).lower() in {"y", "yes", "true", "1"}


def parse_when(value):
    text = clean(value)
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised timestamp: {value!r}")


def to_cents(value):
    """'$12.50', '12.5' or '7' (dollars) -> whole cents."""
    text = clean(value).replace("$", "")
    return int(Decimal(text) * 100)


def _rows(path):
    """Yield CSV rows with trimmed, lower-cased headers and trimmed cells."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for raw in csv.DictReader(fh):
            yield {clean(k).lower(): clean(v) for k, v in raw.items()}


def load_contributors(path):
    registry = {}
    for row in _rows(path):
        cid = norm_id(row.get("contributor_id"))
        registry[cid] = Contributor(
            id=cid,
            name=row.get("name", ""),
            tier=row.get("tier", "").lower(),
            carryover=int(row.get("carryover_cents") or 0),
            active=parse_bool(row.get("active")),
        )
    return registry


def load_entries(path):
    """Work-log entries keyed by entry id; a repeated entry id replaces the earlier row."""
    entries = {}
    for row in _rows(path):
        entries[norm_id(row.get("entry_id"))] = Entry(
            entry_id=norm_id(row.get("entry_id")),
            contributor_id=norm_id(row.get("contributor_id")),
            task_type=row.get("task_type", "").lower(),
            units=int(row.get("units") or 0),
            status=row.get("status", "").lower(),
            completed_at=parse_when(row.get("completed_at")),
        )
    return list(entries.values())


def load_adjustments(path):
    adjustments = []
    for row in _rows(path):
        kind = row.get("kind", "").lower()
        if kind not in ADJUSTMENT_KINDS:
            continue
        adjustments.append(Adjustment(
            contributor_id=norm_id(row.get("contributor_id")),
            kind=kind,
            cents=to_cents(row.get("amount")),
            note=row.get("note", ""),
        ))
    return adjustments


def load_rates(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "task_types": {k.lower(): int(v) for k, v in raw["task_types"].items()},
        "tiers": {k.lower(): int(v) for k, v in raw["tier_percent"].items()},
        "start": date.fromisoformat(raw["period"]["start"]),
        "end": date.fromisoformat(raw["period"]["end"]),
        "min_payout": int(raw["min_payout_cents"]),
    }
