from pathlib import Path

from .loader import load_items, load_responses
from .scoring import grade, model_stats

DATA = Path(__file__).resolve().parent.parent / "data"


def leaderboard(stats):
    # best accuracy first
    ranked = sorted(stats.items(), key=lambda kv: (-kv[1]["accuracy"], kv[0]))
    return [model for model, _ in ranked]


def build_report(data_dir=DATA):
    data_dir = Path(data_dir)
    items = load_items(data_dir / "items.csv")
    responses = load_responses(data_dir / "responses.jsonl")
    graded = grade(items, responses)
    stats = model_stats(graded)
    return {
        "responses": graded,
        "models": stats,
        "leaderboard": leaderboard(stats),
    }
