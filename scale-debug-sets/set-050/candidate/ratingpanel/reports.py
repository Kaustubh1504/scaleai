from collections import Counter, defaultdict
from pathlib import Path

from .loader import latest_only, load_items, load_registry, read_ratings, split_rushed
from .scoring import score_items

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def category_means(items, results):
    by_cat = defaultdict(list)
    for iid, res in results.items():
        if res.consensus is not None:
            by_cat[items[iid].category].append(res.consensus)
    means = {}
    total = 0.0
    for cat in sorted(by_cat):
        for value in by_cat[cat]:
            total += value
        means[cat] = round(total / len(by_cat[cat]), 2)
    return means


def summarize(items, results):
    counts = Counter(res.status.value for res in results.values())
    return {
        "status_counts": dict(sorted(counts.items())),
        "escalated": sorted(iid for iid, res in results.items() if res.status == "escalated"),
        "category_means": category_means(items, results),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    registry = load_registry(data_dir / "annotators.json")
    items = load_items(data_dir / "items.csv")
    kept, rushed = split_rushed(read_ratings(data_dir / "ratings.csv", registry))
    ratings = latest_only(kept)
    results, outliers = score_items(items, ratings)
    rated = Counter(r.annotator_id for r in ratings)
    dropped = Counter(r.annotator_id for r in outliers)
    return {
        "items": {
            iid: {"status": res.status.value, "consensus": res.consensus, "agreement": res.agreement}
            for iid, res in results.items()
        },
        "annotators": {
            aid: {"rated": rated[aid], "rushed": rushed[aid], "outliers": dropped[aid]}
            for aid in sorted(registry)
        },
        "summary": summarize(items, results),
    }
