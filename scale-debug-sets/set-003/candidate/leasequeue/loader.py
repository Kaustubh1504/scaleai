import csv
from datetime import datetime

from .models import Event, Task

TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")
DEFAULT_MAX_ATTEMPTS = 3


def clean(value):
    return (value or "").strip()


def parse_ts(value):
    text = clean(value)
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"bad timestamp {value!r}")


def load_tasks(path):
    tasks = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            max_attempts = clean(row["max_attempts"])
            tasks.append(Task(
                id=clean(row["task_id"]).upper(),
                priority=clean(row["priority"]),
                created_at=parse_ts(row["created_at"]),
                max_attempts=int(max_attempts) if max_attempts else DEFAULT_MAX_ATTEMPTS,
            ))
    return tasks


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            task_id = clean(row["task_id"]).upper()
            events.append(Event(
                ts=parse_ts(row["ts"]),
                worker_id=clean(row["worker_id"]).lower(),
                action=clean(row["action"]).lower(),
                task_id=task_id or None,
            ))
    return events
