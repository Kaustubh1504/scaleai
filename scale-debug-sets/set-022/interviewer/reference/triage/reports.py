from itertools import groupby
from pathlib import Path

from .assigner import assign
from .loader import load_predictions, load_reviewers, load_thresholds
from .models import Route
from .review_queue import build_queue
from .router import route_all

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(decisions, assignments, backlog):
    by_type = {}
    ordered = sorted(decisions, key=lambda d: d.prediction.task_type)
    for task_type, group in groupby(ordered, key=lambda d: d.prediction.task_type):
        group = list(group)
        human = sum(1 for d in group if d.route is Route.HUMAN)
        by_type[task_type] = {
            "auto": len(group) - human,
            "human": human,
            "human_rate": round(human / len(group), 3),
        }
    loads = {rid: len(items) for rid, items in assignments.items()}
    busiest = min(loads, key=lambda rid: (-loads[rid], rid)) if loads else None
    return {"by_task_type": by_type, "busiest_reviewer": busiest, "backlog_size": len(backlog)}


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    thresholds = load_thresholds(data_dir / "thresholds.json")
    predictions = load_predictions(data_dir / "predictions.csv")
    reviewers = load_reviewers(data_dir / "reviewers.csv")

    decisions = route_all(predictions, thresholds)
    queue = build_queue(decisions)
    assignments, backlog = assign(queue, reviewers)
    return {
        "decisions": [
            {"pred_id": d.prediction.pred_id, "route": d.route.value, "reason": d.reason}
            for d in decisions
        ],
        "queue": [d.prediction.pred_id for d in queue],
        "assignments": assignments,
        "backlog": backlog,
        "summary": summarize(decisions, assignments, backlog),
    }
