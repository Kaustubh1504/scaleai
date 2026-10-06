from collections import Counter
from itertools import groupby
from pathlib import Path

from .cache import Memo
from .calibration import bias_for, gold_ratings
from .consensus import resolve
from .loader import counting_ratings, load_config, load_items, load_registry, read_ratings

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATUSES = ("agreed", "contested", "insufficient")


def rubric_summary(results):
    summary = {}
    for rubric, group in groupby(results.values(), key=lambda r: r.rubric):
        counts = Counter(r.status for r in group)
        summary[rubric] = {status: counts.get(status, 0) for status in STATUSES}
    return summary


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    registry = load_registry(data_dir / "annotators.json")
    items = load_items(data_dir / "items.csv")
    raw = read_ratings(sorted(data_dir.glob("ratings_*.csv")))
    ratings = counting_ratings(raw, registry, items, config)
    gold = gold_ratings(ratings, items)

    memo = Memo()
    results = resolve(items, ratings, gold, memo, config)
    rubrics = sorted({item.rubric for item in items.values()})
    bias = {
        aid: {rubric: round(bias_for(memo, gold, items, aid, rubric), 3) for rubric in rubrics}
        for aid in sorted(a for a, active in registry.items() if active)
    }
    return {
        "bias": bias,
        "consensus": {
            iid: {"status": r.status, "score": r.score, "agreement": r.agreement, "votes": r.votes}
            for iid, r in sorted(results.items())
        },
        "summary": {
            "by_rubric": rubric_summary(results),
            "contested": sorted(iid for iid, r in results.items() if r.status == "contested"),
        },
    }
