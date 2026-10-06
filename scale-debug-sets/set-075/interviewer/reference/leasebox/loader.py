import csv
import json
from datetime import datetime, timezone

from .models import Event, Task

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S")
DEFAULT_MAX_ATTEMPTS = 3


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def to_epoch_ms(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass
    raise ValueError(f"unrecognised time: {value!r}")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {"lease_ms": int(raw["lease_seconds"]) * 1000, "checkpoint_ms": to_epoch_ms(raw["checkpoint"])}


def load_workers(path):
    return {norm_id(r["worker_id"]) for r in _rows(path) if clean(r["active"]).lower() in {"y", "yes", "true", "1"}}


def load_tasks(path):
    tasks = {}
    for row in _rows(path):
        tid = norm_id(row["task_id"])
        tasks[tid] = Task(
            id=tid,
            priority=int(clean(row["priority"])),
            enqueued_ms=to_epoch_ms(row["enqueued_at"]),
            max_attempts=int(clean(row["max_attempts"]) or DEFAULT_MAX_ATTEMPTS),
        )
    return tasks


def load_events(path, workers):
    events = []
    for row in _rows(path):
        wid = norm_id(row["worker_id"])
        if wid not in workers:
            continue
        events.append(Event(
            at_ms=int(clean(row["at_ms"])),
            worker_id=wid,
            action=clean(row["action"]).lower(),
            task_id=norm_id(row["task_id"]),
        ))
    return sorted(events, key=lambda e: e.at_ms)
