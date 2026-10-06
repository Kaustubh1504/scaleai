from itertools import groupby
from pathlib import Path

from .evaluate import evaluate
from .loader import load_annotations, load_ground_truth

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _ratio(num, den):
    return round(num / den, 3) if den else 1.0


def annotator_summary(results):
    summary = {}
    ordered = sorted(results, key=lambda r: r.annotator)
    for annotator, group in groupby(ordered, key=lambda r: r.annotator):
        rows = list(group)
        tp = sum(r.tp for r in rows)
        fp = sum(r.fp for r in rows)
        fn = sum(r.fn for r in rows)
        summary[annotator] = {
            "images": len(rows),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
        }
    return summary


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    results = evaluate(load_ground_truth(data_dir / "ground_truth.csv"),
                       load_annotations(data_dir / "annotations.csv"))
    return {
        "images": {
            f"{r.image_id}/{r.annotator}": {"tp": r.tp, "fp": r.fp, "fn": r.fn, "recall": round(r.recall, 3)}
            for r in results
        },
        "flagged": [f"{r.image_id}/{r.annotator}" for r in results if r.flagged],
        "annotators": annotator_summary(results),
    }
