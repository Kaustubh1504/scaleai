from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    label: str
    x1: float
    y1: float
    x2: float
    y2: float


# VERIFIED
def from_normalized_center(label, cx, cy, w, h, width, height):
    """Normalised (cx, cy, w, h) in [0, 1] -> pixel-edge corners on a width x height image."""
    return Box(label, (cx - w / 2) * width, (cy - h / 2) * height, (cx + w / 2) * width, (cy + h / 2) * height)


def area(box):
    return max(0.0, box.x2 - box.x1) * max(0.0, box.y2 - box.y1)


def iou(a, b):
    inter_w = min(a.x2, b.x2) - max(a.x1, b.x1)
    inter_h = min(a.y2, b.y2) - max(a.y1, b.y1)
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    inter = inter_w * inter_h
    return inter / (area(a) + area(b) - inter)
