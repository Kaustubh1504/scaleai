import json
from datetime import datetime
from pathlib import Path

from .assign import assign, due_at, review_queue
from .calibration import calibrate
from .loader import load_predictions, load_reviewers, load_reviews, load_thresholds
from .router import route_all
from .thresholds import ThresholdTable

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _encode(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"cannot serialise {type(obj).__name__}")


def export_json(report):
    return json.dumps(report, default=_encode, indent=2, sort_keys=True)


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    table = ThresholdTable(load_thresholds(data_dir / "thresholds.csv"))
    predictions = load_predictions(data_dir / "predictions.csv")
    reviewers = load_reviewers(data_dir / "reviewers.json")
    decisions = route_all(predictions, table)
    queue = review_queue(predictions, decisions)
    unassigned = assign(queue, reviewers)
    return {
        "routing": {
            iid: {"decision": d.decision, "reason": d.reason, "threshold": d.threshold}
            for iid, d in sorted(decisions.items())
        },
        "assignments": {rid: list(r.assigned) for rid, r in sorted(reviewers.items()) if r.active},
        "unassigned": unassigned,
        "sla": {p.item_id: due_at(p) for p in queue},
        "calibration": calibrate(load_reviews(data_dir / "reviews.csv")),
    }
