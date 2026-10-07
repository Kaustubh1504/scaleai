from datetime import datetime
from pathlib import Path

from .broker import Broker
from .loader import load_events, load_tasks
from .models import DEAD

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AS_OF = datetime(2026, 4, 2, 12, 0)


def _fmt(ts):
    return ts.strftime("%Y-%m-%d %H:%M")


def build_report(data_dir=None, as_of=AS_OF):
    data_dir = Path(data_dir or DATA_DIR)
    broker = Broker(load_tasks(data_dir / "tasks.csv"))
    for event in load_events(data_dir / "events.csv"):
        broker.handle(event)

    # return
    broker.reap(as_of)
    tasks = sorted(broker.tasks.values(), key=lambda t: (t.id))
    print("broker", broker)
    return {
        "dispatch": [[_fmt(ts), worker, task_id] for ts, worker, task_id in broker.dispatch_log],
        "status": {t.id: t.status for t in tasks},
        "attempts": {t.id: t.attempts for t in tasks},
        "dead_letter": [t.id for t in tasks if t.status == DEAD],
        "rejected": [[_fmt(ts), worker, task_id] for ts, worker, task_id in broker.rejected],
        "completed_by": dict(sorted(broker.completed_by.items())),
    }

# print(build_report()["completed_by"])