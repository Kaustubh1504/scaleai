import csv
from datetime import datetime

from .models import Event, Task

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M")


def clean(value):
    return (value or "").strip()


def norm_person(value):
    return clean(value).lower()


# VERIFIED
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
            tasks.append(Task(
                task_id=clean(row["task_id"]).upper(),
                author=norm_person(row["author"]),
                priority=int(clean(row["priority"])),
                submitted_at=parse_time(row["submitted_at"]),
            ))
    return tasks


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            events.append(Event(
                at=parse_time(row["at"]),
                task_id=clean(row["task"]).upper(),
                actor=norm_person(row["actor"]),
                action=clean(row["action"]).lower(),
            ))
    return events
