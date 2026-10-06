import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

REVIEW_CUTOFF = date(2026, 5, 10)
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")
COORDS = ("x_min", "y_min", "x_max", "y_max")


@dataclass(frozen=True)
class Box:
    label: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int


def _clean(value):
    return (value or "").strip()


def parse_date(value):
    text = _clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"bad date {value!r}")


# VERIFIED
def within_cutoff(submitted):
    return submitted <= REVIEW_CUTOFF


def _box(row):
    values = [_clean(row[c]) for c in COORDS]
    if not all(values):
        return None
    return Box(_clean(row["label"]).lower(), *(int(v) for v in values))


def load_ground_truth(path):
    """image_id -> [Box] in file order."""
    gt = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            box = _box(row)
            if box is not None:
                gt[_clean(row["image_id"]).lower()].append(box)
    return dict(gt)


def load_annotations(path):
    """(image_id, annotator) -> [Box] in file order, after the cutoff filter."""
    preds = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            box = _box(row)
            if box is None or not within_cutoff(parse_date(row["submitted"])):
                continue
            key = (_clean(row["image_id"]).lower(), _clean(row["annotator"]).lower())
            preds[key].append(box)
    return dict(preds)
