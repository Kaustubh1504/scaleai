import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


@dataclass
class Contributor:
    contributor_id: str
    name: str
    account_no: int
    method: str


@dataclass
class Rate:
    project: str
    per_task: Decimal
    min_seconds: int


@dataclass
class WorkEntry:
    entry_id: str
    contributor_id: str
    project: str
    submitted_at: datetime
    duration_ms: int
    status: str


@dataclass
class Period:
    start: date
    end: date
    minimum_payout: Decimal


def clean(value):
    return (value or "").strip()


# VERIFIED
def parse_amount(value):
    text = clean(value).replace("$", "").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        return -Decimal(text[1:-1])
    return Decimal(text)


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_period(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Period(date.fromisoformat(raw["start"]), date.fromisoformat(raw["end"]),
                  parse_amount(raw["minimum_payout"]))


def load_contributors(path):
    return {
        clean(row["contributor_id"]).upper(): Contributor(
            clean(row["contributor_id"]).upper(), clean(row["name"]),
            clean(row["account_no"]), clean(row["method"]).lower())
        for row in _rows(path)
    }


def load_rates(path):
    return {
        clean(row["project"]).lower(): Rate(clean(row["project"]).lower(), parse_amount(row["rate_per_task"]),
                                            int(clean(row["min_seconds"])))
        for row in _rows(path)
    }


def load_work(path):
    return [
        WorkEntry(
            entry_id=clean(row["entry_id"]).upper(),
            contributor_id=clean(row["contributor_id"]).upper(),
            project=clean(row["project"]).lower(),
            submitted_at=parse_time(row["submitted_at"]),
            duration_ms=int(clean(row["duration_ms"])),
            status=clean(row["status"]).lower(),
        )
        for row in _rows(path)
    ]


def load_adjustments(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return [(clean(a["contributor_id"]), parse_amount(a["amount"])) for a in raw["adjustments"]]
