import csv
from datetime import datetime
from pathlib import Path

from .models import Event, Session

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def norm_session(value):
    return clean(value).upper()


def parse_time(text):
    text = clean(text)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time {text!r}")


def load_sessions(path=None):
    sessions = {}
    with open(path or DATA_DIR / "sessions.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = norm_session(row["session_id"])
            sessions[sid] = Session(sid, clean(row["title"]), int(clean(row["capacity"])), parse_time(row["starts_at"]))
    return sessions


def load_events(path=None):
    events = []
    with open(path or DATA_DIR / "events.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            seats = clean(row["seats"])
            events.append(Event(
                id=clean(row["event_id"]),
                at=parse_time(row["at"]),
                action=clean(row["action"]).lower(),
                session_id=row["session_id"].upper(),
                attendee=clean(row["attendee"]).lower(),
                seats=int(seats) if seats else 1,
            ))
    return events
