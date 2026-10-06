from collections import Counter
from pathlib import Path

from .backlog import waiting_queue
from .loader import load_events, load_tasks
from .machine import ReviewMachine
from .metrics import cycle_hours, reviewer_stats
from .models import State

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _fmt(ts):
    return ts.strftime("%Y-%m-%d %H:%M")


def summarize(tasks):
    by_state = Counter(t.state.value for t in tasks)
    approved = sum(1 for t in tasks if t.state == "approved")
    rejected = sum(1 for t in tasks if t.state is State.REJECTED)
    decided = approved + rejected
    return {
        "by_state": dict(sorted(by_state.items())),
        "approval_rate": round(approved / decided, 3) if decided else None,
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    machine = ReviewMachine(load_tasks(data_dir / "tasks.csv"))
    for event in load_events(data_dir / "events.csv"):
        machine.handle(event)
    tasks = sorted(machine.tasks.values(), key=lambda t: int(t.task_id[1:]))
    return {
        "states": {t.task_id: t.state.value for t in tasks},
        "revisions": {t.task_id: t.revision for t in tasks},
        "rejected": [[_fmt(e.at), e.task_id, e.actor, e.action, reason] for e, reason in machine.rejected],
        "history": {t.task_id: [s.value for s in t.history] for t in tasks},
        "queue": waiting_queue(tasks),
        "reviewers": reviewer_stats(machine.accepted),
        "cycle_hours": cycle_hours(tasks),
        "summary": summarize(tasks),
    }
