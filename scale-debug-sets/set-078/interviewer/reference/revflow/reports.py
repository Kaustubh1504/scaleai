from pathlib import Path

from .backlog import build_queue
from .loader import load_events, load_people, load_settings, load_tasks
from .replay import replay
from .stats import review_minutes, reviewer_decisions

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def cycle_hours(tasks):
    """Approved task -> hours from creation to approval."""
    return {
        tid: round((t.approved_at - t.created).total_seconds() / 3600, 2)
        for tid, t in sorted(tasks.items()) if t.approved_at is not None
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    settings = load_settings(data_dir / "settings.json")
    people = load_people(data_dir / "people.json")
    tasks = load_tasks(data_dir / "tasks.csv")
    transitions, violations = replay(load_events(data_dir / "events.csv"), tasks, people, settings)
    return {
        "states": {tid: tasks[tid].state.value for tid in sorted(tasks)},
        "rework": {tid: t.rework for tid, t in sorted(tasks.items()) if t.rework},
        "violations": violations,
        "reviewers": reviewer_decisions(transitions, people),
        "review_minutes": review_minutes(transitions),
        "queue": build_queue(tasks, settings["paused"]),
        "cycle_hours": cycle_hours(tasks),
    }
