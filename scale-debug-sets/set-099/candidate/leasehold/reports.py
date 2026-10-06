from collections import defaultdict
from pathlib import Path

from .broker import Broker
from .loader import load_events, load_lease_seconds, load_tasks, load_workers, parse_time

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
END_OF_DAY = "2026-05-01 12:00"


def ack_times(tasks):
    """task type -> mean seconds from first claim to ack, over done tasks."""
    spans = defaultdict(list)
    for task in tasks.values():
        if task.status == "done":
            spans[task.type].append(int((task.finished_at - task.first_claimed_at).total_seconds()))
    return {t: round(sum(s) // len(s), 1) for t, s in sorted(spans.items())}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    tasks = load_tasks(data_dir / "tasks.csv")
    broker = Broker(tasks, load_workers(data_dir / "workers.json"), load_lease_seconds(data_dir / "queue.json"))
    for ev in load_events(data_dir / "events.csv"):
        broker.handle(ev)
    broker.reap(parse_time(END_OF_DAY))
    return {
        "dispatch": broker.dispatch,
        "expired": broker.expired,
        "rejected": broker.rejected,
        "status": {tid: t.status for tid, t in sorted(tasks.items())},
        "attempts": {tid: t.attempts for tid, t in sorted(tasks.items())},
        "dead_letter": sorted(tid for tid, t in tasks.items() if t.status == "dead"),
        "mean_ack_seconds": ack_times(tasks),
    }
