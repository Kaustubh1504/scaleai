import csv
from dataclasses import dataclass

from .geometry import Box


@dataclass(frozen=True)
class GroundTruth:
    gt_id: str
    image_id: str
    label: str
    box: Box


@dataclass(frozen=True)
class Prediction:
    pred_id: str
    image_id: str
    annotator: str
    label: str
    box: Box


def clean(value):
    return (value or "").strip()


# VERIFIED
def xywh_to_xyxy(x, y, w, h):
    """COCO-style (left, top, width, height) to corner coordinates."""
    return Box(x, y, x + w, y + h)


def _numbers(row, keys):
    values = [clean(row[k]) for k in keys]
    if any(v == "" for v in values):
        return None
    return [float(v) for v in values]


def load_ground_truth(path):
    boxes = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            coords = _numbers(row, ("x1", "y1", "x2", "y2"))
            if coords is None:
                continue
            boxes.append(GroundTruth(clean(row["gt_id"]).lower(), clean(row["image_id"]).upper(),
                                     clean(row["label"]).lower(), Box(*coords)))
    return boxes


def load_predictions(path):
    preds = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            coords = _numbers(row, ("x", "y", "w", "h"))
            if coords is None:
                continue
            preds.append(Prediction(
                pred_id=clean(row["pred_id"]).lower(),
                image_id=clean(row["image_id"]).upper(),
                annotator=clean(row["annotator"]).lower(),
                label=clean(row["label"]).lower(),
                box=xywh_to_xyxy(*coords),
            ))
    return preds
