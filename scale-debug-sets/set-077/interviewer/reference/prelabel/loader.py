import csv
import json
from collections import defaultdict

from .geometry import Box, from_normalized_center

MIN_SCORE = 0.30


def _clean(value):
    return str(value if value is not None else "").strip()


def load_images(path):
    """image_id -> (width, height)."""
    images = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            images[_clean(row["image_id"]).lower()] = (int(_clean(row["width"])), int(_clean(row["height"])))
    return images


def load_ground_truth(path, images):
    """image_id -> [Box] in file order, for known images only."""
    gt = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            image = _clean(row["image_id"]).lower()
            if image not in images:
                continue
            coords = [float(_clean(row[k])) for k in ("x1", "y1", "x2", "y2")]
            gt[image].append(Box(_clean(row["label"]).lower(), *coords))
    return {image: gt.get(image, []) for image in images}


def parse_score(value):
    text = _clean(value)
    return float(text) if text else None


def load_predictions(path, images):
    """model -> image_id -> [(score, Box)] in file order, kept predictions only."""
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    preds = defaultdict(lambda: defaultdict(list))
    for row in rows:
        image = _clean(row["image"]).lower()
        score = parse_score(row.get("score"))
        if image not in images or score is None or score < MIN_SCORE:
            continue
        width, height = images[image]
        box = from_normalized_center(_clean(row["label"]).lower(), *row["box"], width, height)
        preds[_clean(row["model"]).lower()][image].append((score, box))
    return preds
