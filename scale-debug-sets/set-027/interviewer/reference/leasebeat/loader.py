import csv
from datetime import datetime, timezone

from .models import Event, Task

DEFAULT_MAX_ATTEMPTS = 2
FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M")


def clean(value):
    return str(value if value is not None else "").strip()


# VERIFIED
def to_ms(value):
    """Epoch milliseconds (UTC) from an epoch-ms string or one of FORMATS."""
    text = clean(value)
    if text.isdigit():
        return int(text)
    for fmt in FORMATS:
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        return int(dt.timestamp() * 1000)
    raise ValueError(f"unrecognised time {value!r}")


def fmt_ms(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%H:%M:%S")


def load_tasks(path):
    tasks = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            max_attempts = clean(row["max_attempts"])
            tasks.append(Task(
                task_id=clean(row["task_id"]).upper(),
                priority=int(clean(row["priority"])),
                enqueued_ms=to_ms(row["enqueued_at"]),
                max_attempts=int(max_attempts) if max_attempts else DEFAULT_MAX_ATTEMPTS,
            ))
    return tasks


def load_events(path):
    events = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            task = clean(row["task_id"]).upper()
            events.append(Event(
                ts_ms=to_ms(row["ts"]),
                worker_id=clean(row["worker"]).lower(),
                action=clean(row["action"]).lower(),
                task_id=task or None,
            ))
    return events
