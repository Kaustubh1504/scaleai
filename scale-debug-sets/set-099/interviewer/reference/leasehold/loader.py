import csv
import json
from datetime import datetime

from .models import Event, Task

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return str(value if value is not None else "").strip()


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time: {value!r}")


def load_tasks(path):
    tasks = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = clean(row["task_id"]).upper()
            attempts = clean(row["max_attempts"])
            tasks[tid] = Task(
                id=tid,
                type=clean(row["type"]).lower(),
                priority=int(clean(row["priority"])),
                created_at=parse_time(row["created_at"]),
                max_attempts=int(attempts) if attempts else 3,
            )
    return tasks


def load_workers(path):
    """worker id -> set of task types, active workers only."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        clean(w["id"]).lower(): {clean(t).lower() for t in w["types"]}
        for w in raw
        if w.get("active", True) is True
    }


def load_lease_seconds(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {clean(k).lower(): int(v) for k, v in raw["lease_seconds"].items()}


def load_events(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            Event(
                at=parse_time(row["at"]),
                worker=clean(row["worker"]).lower(),
                action=clean(row["action"]).lower(),
                task_id=clean(row["task_id"]).upper() or None,
            )
            for row in csv.DictReader(fh)
        ]
