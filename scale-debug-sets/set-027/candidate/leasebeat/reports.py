import statistics
from pathlib import Path

from .broker import Broker
from .loader import load_events, load_tasks, to_ms

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
END_OF_LOG = "2026-04-01T08:10:00Z"


def mean_wait_seconds(tasks):
    waits = [t.first_leased_ms - t.enqueued_ms for t in tasks if t.first_leased_ms is not None]
    return round(statistics.mean(waits), 1) if waits else None


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    tasks = load_tasks(data_dir / "tasks.csv")
    broker = Broker(tasks).replay(load_events(data_dir / "events.csv"), to_ms(END_OF_LOG))
    ordered = sorted(broker.tasks.values(), key=lambda t: t.task_id)
    return {
        "dispatch": broker.dispatch,
        "heartbeats": broker.heartbeats,
        "rejected_acks": broker.rejected_acks,
        "status": {t.task_id: t.status for t in ordered},
        "attempts": {t.task_id: t.attempts for t in ordered},
        "dead_letter": [t.task_id for t in ordered if t.status == "dead"],
        "completed_by": {wid: list(w.completed) for wid, w in sorted(broker.workers.items()) if w.completed},
        "mean_wait_s": mean_wait_seconds(ordered),
    }
