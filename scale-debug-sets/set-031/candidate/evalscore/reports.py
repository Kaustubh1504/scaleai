from collections import Counter
from pathlib import Path

from .loader import load_attempts, load_items
from .models import Status
from .scoring import group_attempts, score_model

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def category_accuracy(items, correct):
    totals, earned = {}, {}
    for item in items:
        totals[item.category] = totals.get(item.category, 0.0) + item.weight
        if item.item_id in correct:
            earned[item.category] = earned.get(item.category, 0.0) + item.weight
    return {cat: round(earned.get(cat, 0.0) / totals[cat], 3) for cat in sorted(totals)}


def status_counts(attempts):
    counts = Counter(att.status for att in attempts)
    return {status.value: counts.get(status, 0) for status in Status}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    items = load_items(data_dir / "items.json")
    attempts = load_attempts(data_dir / "attempts.csv")
    grouped = group_attempts(attempts)

    models = {}
    for model in sorted(grouped):
        score = score_model(model, items, grouped[model])
        models[model] = {
            "accuracy": round(score.earned / score.possible, 3) if score.possible else 0.0,
            "correct": sorted(score.correct),
            "unparsed": sorted(score.unparsed),
            "failed": sorted(score.failed),
            "by_category": category_accuracy(items, set(score.correct)),
        }
    return {
        "models": models,
        "status_counts": {m: status_counts([a for a in attempts if a.model == m]) for m in sorted(grouped)},
        "leaderboard": sorted(models, key=lambda m: (-models[m]["accuracy"], m)),
    }
