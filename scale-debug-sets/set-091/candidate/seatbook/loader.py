import csv
from datetime import datetime

from .models import Hold, Member, Session

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


# VERIFIED
def parse_when(value):
    text = clean(value)
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_sessions(path):
    sessions = {}
    for row in read_rows(path):
        sid = clean(row["session_id"]).upper()
        capacity = clean(row["capacity"])
        sessions[sid] = Session(sid, clean(row["room"]), int(capacity) if capacity else 0)
    return sessions


def load_members(path):
    members = {}
    for row in read_rows(path):
        mid = clean(row["member_id"]).lower()
        tier = clean(row.get("tier")).lower() or "standard"
        members[mid] = Member(mid, clean(row["name"]), tier)
    return members


def load_holds(path, sessions, members):
    holds = []
    for row in read_rows(path):
        seats = clean(row["seats"])
        sid = clean(row["session_id"]).upper()
        mid = clean(row["member_id"]).lower()
        if not seats or sid not in sessions or mid not in members:
            continue
        holds.append(Hold(
            hold_id=clean(row["hold_id"]).upper(),
            session_id=sid,
            member_id=mid,
            seats=int(seats),
            placed_at=parse_when(row["placed_at"]),
            confirmed_at=parse_when(row["confirmed_at"]),
        ))
    return holds
