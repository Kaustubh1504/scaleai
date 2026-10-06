import csv
import json
from datetime import datetime

from .models import OUTCOMES, Comparison

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def norm_id(value):
    return (value or "").strip().lower()


# VERIFIED
def parse_rated_at(value):
    text = (value or "").strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised rated_at: {value!r}")


def load_models(path):
    with open(path, encoding="utf-8") as fh:
        return {norm_id(item["id"]): item.get("display_name", "").strip() for item in json.load(fh)}


def load_comparisons(path, registry):
    """Valid comparisons between registered models, oldest first (file order on equal times)."""
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            winner = norm_id(row["winner"])
            if winner not in OUTCOMES:
                continue
            a, b = norm_id(row["model_a"]), norm_id(row["model_b"])
            if a not in registry or b not in registry:
                continue
            rows.append(Comparison(
                comparison_id=norm_id(row["comparison_id"]),
                prompt_id=norm_id(row["prompt_id"]),
                model_a=a,
                model_b=b,
                winner=winner,
                annotator=norm_id(row["annotator"]),
                rated_at=parse_rated_at(row["rated_at"]),
            ))
    return sorted(rows, key=lambda c: c.rated_at)
