import csv
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Request:
    request_id: str
    tenant: str
    ts_ms: int


@dataclass(frozen=True)
class UsageRow:
    day: object
    tenant: str
    endpoint: str
    tokens: int


DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y")


# VERIFIED
def parse_day(value):
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date {value!r}")


def load_requests(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [Request(
            request_id=row["request_id"].strip().upper(),
            tenant=row["tenant"].strip().lower(),
            ts_ms=int(row["ts_ms"].strip()),
        ) for row in csv.DictReader(fh)]


def load_usage(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [UsageRow(
            day=parse_day(row["date"]),
            tenant=row["tenant"].strip().lower(),
            endpoint=row["endpoint"].strip().lower(),
            tokens=int(row["tokens"].strip().replace(",", "")),
        ) for row in csv.DictReader(fh)]
