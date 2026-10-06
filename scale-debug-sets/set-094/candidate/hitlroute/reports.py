from pathlib import Path

from .assign import assign_expert_queue
from .calibration import label_confusions, model_calibration
from .loader import load_policy, load_predictions, load_reviewers, load_reviews
from .policy import Policy
from .router import route_all

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    policy = Policy(*load_policy(data_dir / "policy.json"))
    predictions = load_predictions(data_dir / "predictions.csv")
    reviewers = load_reviewers(data_dir / "reviewers.csv")
    reviews = load_reviews(data_dir / "reviews.csv")

    decisions = route_all(predictions, policy)
    assignments, backlog = assign_expert_queue(predictions, decisions, reviewers)
    return {
        "decisions": {
            item_id: {"route": d.route.value, "reason": d.reason}
            for item_id, d in sorted(decisions.items())
        },
        "assignments": assignments,
        "backlog": backlog,
        "calibration": {
            "models": model_calibration(reviews),
            "confusions": label_confusions(reviews),
        },
    }
