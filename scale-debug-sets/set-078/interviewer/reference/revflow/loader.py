import csv
import json

from .clock import parse_ts
from .models import Event, Person, State, Task

TRUTHY = {"true", "yes", "y", "1"}


def clean(value):
    return (value or "").strip()


def parse_flag(value, default=False):
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in TRUTHY
    return bool(value)


def load_settings(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "as_of": parse_ts(raw["as_of"]),
        "claim_ttl_minutes": int(raw["claim_ttl_minutes"]),
        "max_rework": int(raw["max_rework"]),
        "paused": {clean(name).lower() for name, p in raw["projects"].items() if parse_flag(p.get("paused"))},
    }


def load_people(path):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    people = {}
    for r in rows:
        pid = clean(r["id"]).lower()
        people[pid] = Person(pid, clean(r["role"]).lower(), parse_flag(r.get("active"), default=True))
    return people


def load_tasks(path):
    tasks = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = clean(row["task_id"]).upper()
            state = clean(row["state"]).lower() or "queued"
            tasks[tid] = Task(tid, clean(row["project"]).lower(), int(clean(row["priority"])),
                              parse_ts(row["created"]), State(state))
    return tasks


def load_events(path):
    """Events in file order. Exact duplicates (after cleaning) are dropped; the first copy is kept."""
    events, seen = [], set()
    with open(path, newline="", encoding="utf-8") as fh:
        for line, row in enumerate(csv.DictReader(fh), start=2):
            ts = parse_ts(row["ts"])
            task_id = clean(row["task_id"]).upper()
            actor = clean(row["actor"]).lower()
            action = clean(row["action"]).lower()
            key = (ts, task_id, actor, action)
            if key in seen:
                continue
            seen.add(key)
            events.append(Event(line, ts, task_id, actor, action))
    return events
