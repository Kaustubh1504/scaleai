from collections import Counter
from pathlib import Path

from .engine import replay
from .loader import load_events, load_members, load_tasks
from .metrics import annotator_table, cycle_hours, reviewer_table, state_counts
from .models import State

DATA = Path(__file__).resolve().parent.parent / "data"


def summarize(tasks):
    approved = [t for t in tasks.values() if t.state is State.APPROVED]
    first_pass = [t for t in approved if t.rework == 0]
    hours = [cycle_hours(t) for t in approved]
    open_by_queue = Counter(t.queue for t in tasks.values() if t.is_open)
    return {
        "state_counts": state_counts(tasks),
        "first_pass_rate": round(len(first_pass) / len(approved), 3) if approved else None,
        "avg_cycle_hours": round(sum(hours) / len(hours), 2) if hours else None,
        "open_by_queue": dict(sorted(open_by_queue.items())),
    }


def build_report(data_dir=DATA):
    data_dir = Path(data_dir)
    members = load_members(data_dir / "members.json")
    tasks = load_tasks(data_dir / "tasks.csv")
    events = load_events(data_dir / "events.csv")
    applied, invalid = replay(tasks, members, events)
    return {
        "tasks": {
            tid: {
                "state": t.state.value,
                "rework": t.rework,
                "assignee": t.assignee,
                "transitions": len(t.history),
            }
            for tid, t in sorted(tasks.items())
        },
        "invalid": invalid,
        "reviewers": reviewer_table(members, applied),
        "annotators": annotator_table(members, tasks, applied),
        "summary": summarize(tasks),
    }
