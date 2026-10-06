from collections import Counter
from pathlib import Path

from .aggregate import group_by, sample_scores, weighted_mean
from .loader import load_judgments, load_samples, load_weights

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    weights = load_weights(data_dir / "rubric.json")
    samples = load_samples(data_dir / "samples.csv", weights)
    judgments, failures = load_judgments(data_dir / "judgments.jsonl", samples)

    scores = sample_scores(judgments)
    shown = {sid: round(scores[sid], 2) for sid in sorted(scores)}
    scored = [samples[sid] for sid in sorted(scores)]

    by_model = group_by(scored, lambda s: s.model)
    models = sorted({s.model for s in scored})
    leaderboard = {m: round(weighted_mean(by_model[m], scores, weights), 3) for m in models}

    by_category = group_by(scored, lambda s: s.category)
    categories = {
        c: {"n": len(items), "mean": round(sum(scores[s.sample_id] for s in items) / len(items), 3)}
        for c, items in sorted(by_category.items())
    }
    return {
        "samples": shown,
        "unscored": sorted(set(samples) - set(scores)),
        "parse_failures": sorted(failures),
        "judges": dict(sorted(Counter(j.judge for j in judgments).items())),
        "leaderboard": leaderboard,
        "categories": categories,
    }
