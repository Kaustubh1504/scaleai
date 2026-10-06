from collections import Counter
from pathlib import Path

from .loader import load_config, load_events, load_tasks, load_workers
from .replay import replay

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def task_view(tasks):
    return {
        tid: {"state": t.state, "owner": t.owner, "attempts": t.attempts}
        for tid, t in sorted(tasks.items())
    }


def wait_stats(tasks):
    waits = [t.first_claim_ms - t.enqueued_ms for t in tasks.values() if t.first_claim_ms is not None]
    if not waits:
        return {"mean_s": None, "max_s": None}
    return {
        "mean_s": round(sum(waits) / len(waits) / 1000, 1),
        "max_s": round(max(waits) / 1000, 1),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    workers = load_workers(data_dir / "workers.csv")
    tasks = load_tasks(data_dir / "tasks.csv")
    events = load_events(data_dir / "events.csv", workers)
    broker, polls, rejected, checkpoint = replay(tasks, events, config)

    done_by = Counter(t.completed_by for t in broker.tasks.values() if t.state == "done")
    return {
        "final": task_view(broker.tasks),
        "polls": [[wid, tid] for wid, tid in polls],
        "checkpoint": task_view(checkpoint),
        "summary": {
            "completed_by": dict(sorted(done_by.items())),
            "dead": sorted(tid for tid, t in broker.tasks.items() if t.state == "dead"),
            "rejected": {code: rejected.get(code, 0) for code in ("expired", "not_owner", "invalid")},
            "wait": wait_stats(broker.tasks),
        },
    }
