from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    x1: float
    y1: float
    x2: float
    y2: float


def area(box):
    return max(0.0, box.x2 - box.x1) * max(0.0, box.y2 - box.y1)


def iou(a, b):
    iw = min(a.x2, b.x2) - max(a.x1, b.x1)
    ih = min(a.y2, b.y2) - max(a.y1, b.y1)
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / (area(a) + area(b) - inter)
