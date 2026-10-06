import csv
import json
from datetime import datetime

from .models import Event, Member, TaskRecord

FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


# VERIFIED
def parse_when(value):
    text = clean(value)
    for fmt in FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp: {value!r}")


def load_members(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    members = {}
    for item in raw:
        mid = clean(item["id"]).lower()
        members[mid] = Member(
            id=mid,
            name=clean(item.get("name")),
            role=clean(item.get("role")).lower(),
            active=item.get("active", True) is True,
        )
    return members


def load_tasks(path):
    tasks = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = clean(row["task_id"]).upper()
            tasks[tid] = TaskRecord(tid, clean(row["queue"]).lower(), parse_when(row["created_at"]))
    return tasks


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            eid = clean(row["event_id"]).upper()
            events.append(Event(
                event_id=eid,
                seq=int(eid.lstrip("E")),
                task_id=clean(row["task_id"]).upper(),
                actor=clean(row["actor"]).lower(),
                action=clean(row["action"]).lower(),
                at=parse_when(row["at"]),
            ))
    # replay order: timestamp first, then event number
    events.sort(key=lambda ev: (ev.at, ev.event_id))
    return events
