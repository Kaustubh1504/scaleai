from collections import defaultdict
from pathlib import Path

from .grading import grade_all
from .loader import load_attempts, load_items

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    items = load_items(data_dir / "items.csv")
    grades = grade_all(items, load_attempts(data_dir / "responses"))
    by_model = defaultdict(list)
    for g in grades:
        by_model[g.model].append(g)

    total_weight = sum(item.weight for item in items.values())
    correct, unscored, scores, categories = {}, {}, {}, {}
    for model, gs in sorted(by_model.items()):
        hits = [g for g in gs if g.outcome == "correct"]
        correct[model] = [g.item_id for g in hits]
        unscored[model] = {
            "errored": [g.item_id for g in gs if g.outcome == "errored"],
            "unparsed": [g.item_id for g in gs if g.outcome == "unparsed"],
        }
        scores[model] = round(sum(items[g.item_id].weight for g in hits) / total_weight, 3)
        per_cat = defaultdict(lambda: [0, 0])
        for g in gs:
            cat = per_cat[items[g.item_id].category]
            cat[0] += g.outcome == "correct"
            cat[1] += 1
        categories[model] = {c: round(h / n, 3) for c, (h, n) in sorted(per_cat.items())}

    leaderboard = sorted(scores, key=lambda m: (-scores[m], m))
    return {
        "correct": correct,
        "unscored": unscored,
        "weighted_scores": scores,
        "category_accuracy": categories,
        "leaderboard": leaderboard,
    }
