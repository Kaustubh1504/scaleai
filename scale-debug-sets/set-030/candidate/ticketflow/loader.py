import csv
import json
from datetime import datetime

from .models import Event, new_ticket

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M")


def clean(value):
    return str(value if value is not None else "").strip()


def parse_ts(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time {value!r}")


# VERIFIED
def parse_flag(value):
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


def load_people(path):
    with open(path, encoding="utf-8") as fh:
        return {clean(p["id"]): clean(p["role"]).lower() for p in json.load(fh)}


def load_tickets(path):
    tickets = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = clean(row["ticket_id"]).upper()
            tickets[tid] = new_ticket(tid, int(clean(row["severity"])), parse_flag(row["vip"]), parse_ts(row["opened_at"]))
    return tickets


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            events.append(Event(
                seq=int(clean(row["seq"])),
                ts=parse_ts(row["ts"]),
                ticket_id=clean(row["ticket_id"]).upper(),
                actor=clean(row["actor"]).lower(),
                action=clean(row["action"]).lower(),
                value=clean(row["value"]).lower(),
            ))
    return events
