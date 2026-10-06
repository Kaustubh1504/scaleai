from collections import Counter
from pathlib import Path

from .registry import load_annotators, load_config, load_items
from .scoring import annotator_agreement, contested
from .screening import latest_only, screen
from .vendors import read_vendor_a, read_vendor_b
from .voting import resolve, within_window

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATUSES = ("accepted", "escalated", "pending")


def queue_report(name, items, results, votes):
    q_results = {iid: r for iid, r in results.items() if items[iid].queue == name}
    q_votes = [v for v in votes if v.item_id in q_results and within_window(v, items[v.item_id])]
    counts = Counter(r.status for r in q_results.values())
    return {
        "items": {iid: {"status": r.status, "label": r.label, "agreement": r.agreement, "votes": r.votes}
                  for iid, r in q_results.items()},
        "status_counts": {s: counts.get(s, 0) for s in STATUSES},
        "agreement": annotator_agreement(q_results, q_votes),
        "contested": contested(q_results),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    annotators = load_annotators(data_dir / "annotators.json")
    weights, queues, aliases = load_config(data_dir / "queues.json")
    items = load_items(data_dir / "items.csv", queues)
    kept_a, rejected_a = screen(read_vendor_a(data_dir / "vendor_a.csv"), items, annotators, queues, aliases)
    kept_b, rejected_b = screen(read_vendor_b(data_dir / "vendor_b.jsonl"), items, annotators, queues, aliases)
    votes, superseded = latest_only(kept_a + kept_b)
    results = resolve(items, votes, annotators, weights, queues)
    return {
        "rejected": {"vendor_a": dict(sorted(rejected_a.items())), "vendor_b": dict(sorted(rejected_b.items()))},
        "superseded": superseded,
        "queues": {name: queue_report(name, items, results, votes) for name in sorted(queues)},
    }
