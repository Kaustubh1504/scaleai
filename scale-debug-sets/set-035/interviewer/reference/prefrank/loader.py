import csv
import json
from collections import Counter

from .models import Comparison

TRUTHY = {"true", "yes", "y", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def flag(value):
    if isinstance(value, bool):
        return value
    return clean(value).lower() in TRUTHY


def load_raters(path):
    """Ids of raters who passed the attention check."""
    with open(path, encoding="utf-8") as fh:
        return {clean(r["id"]).lower() for r in json.load(fh) if flag(r.get("attention_passed"))}


def load_comparisons(path, raters):
    """Return (valid comparisons in file order, Counter of exclusion reasons)."""
    valid, excluded = [], Counter()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            a, b = clean(row["model_a"]).lower(), clean(row["model_b"]).lower()
            pref = clean(row["preference"]).lower()
            rater = clean(row["rater"]).lower()
            if flag(row["skipped"]):
                excluded["skipped"] += 1
            elif rater not in raters:
                excluded["rater"] += 1
            elif a == b or pref not in ("a", "b", "tie"):
                excluded["invalid"] += 1
            else:
                winner = {"a": a, "b": b}.get(pref)
                valid.append(Comparison(clean(row["comparison_id"]).lower(), int(clean(row["round"])),
                                        a, b, winner, rater))
    return valid, excluded
