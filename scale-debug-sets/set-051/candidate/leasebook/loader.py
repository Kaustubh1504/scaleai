import csv
from datetime import datetime

from .models import Event, Task

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")
DEFAULT_MAX_ATTEMPTS = 2


def clean(value):
    return (value or "").strip()


def norm_task(value):
    return clean(value).upper()


def norm_name(value):
    return clean(value).lower()


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised time: {value!r}")


def load_tasks(path):
    tasks = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            raw_max = clean(row["max_attempts"])
            tasks.append(Task(
                id=norm_task(row["task_id"]),
                queue=norm_name(row["queue"]),
                priority=int(clean(row["priority"])),
                created_at=parse_time(row["created_at"]),
                max_attempts=int(raw_max) if raw_max else DEFAULT_MAX_ATTEMPTS,
            ))
    return tasks


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            events.append(Event(
                at=parse_time(row["at"]),
                worker=norm_name(row["worker"]),
                action=norm_name(row["action"]),
                queue=norm_name(row["queue"]),
                task_id=clean(row["task"]),
            ))
    return events
