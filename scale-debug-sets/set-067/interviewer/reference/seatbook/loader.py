import csv
from datetime import datetime

from .models import Request, Seat

TS_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def parse_ts(value):
    text = clean(value)
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def load_seats(path):
    seats = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            seats.append(Seat(
                section=clean(row["section"]).upper(),
                row=clean(row["row"]).upper(),
                number=int(row["number"]),
                tier=clean(row["tier"]).lower(),
            ))
    return seats


def load_requests(path):
    requests = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            requests.append(Request(
                request_id=clean(row["request_id"]).upper(),
                ts=parse_ts(row["ts"]),
                action=clean(row["action"]).lower(),
                customer=clean(row["customer"]).lower(),
                section=clean(row["section"]).upper(),
                quantity=int(clean(row["quantity"]) or 1),
            ))
    # sorted() is stable, so requests with the same timestamp keep file order
    return sorted(requests, key=lambda r: r.ts)
