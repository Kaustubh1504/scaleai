from collections import Counter
from pathlib import Path

from .assign import assign_reviewers
from .loader import load_policies, load_predictions, load_reviewers
from .models import Decision
from .router import route_all
from .worklist import build_worklists

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(routed, backlog):
    per_task = Counter(r.prediction.task for r in routed)
    auto = Counter(r.prediction.task for r in routed if r.decision is Decision.AUTO_ACCEPT)
    review = [r for r in routed if r.decision is Decision.HUMAN_REVIEW]
    scored = [r.prediction.confidence for r in review if r.prediction.confidence is not None]
    return {
        "auto_accept_rate": {task: round(auto[task] / n, 3) for task, n in sorted(per_task.items())},
        "review_load": dict(sorted(Counter(r.reviewer for r in review if r.reviewer).items())),
        "backlog": len(backlog),
        "mean_review_confidence": round(sum(scored) / len(scored), 3) if scored else None,
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    policies = load_policies(data_dir / "policies.json")
    reviewers = load_reviewers(data_dir / "reviewers.json")
    routed = route_all(load_predictions(data_dir / "predictions.csv", policies), policies)
    backlog = assign_reviewers(routed, reviewers)
    return {
        "routing": {r.prediction.item_id: {"task": r.prediction.task, "decision": r.decision.value, "reason": r.reason}
                    for r in routed},
        "assignments": {r.prediction.item_id: r.reviewer for r in routed if r.decision is Decision.HUMAN_REVIEW},
        "backlog": backlog,
        "worklists": build_worklists(routed),
        "summary": summarize(routed, backlog),
    }
