import copy
from dataclasses import dataclass


@dataclass
class Box:
    image: str
    box_id: str | None
    label: str
    x1: float
    y1: float
    x2: float
    y2: float


def from_xywh(image, box_id, label, bbox):
    x, y, w, h = (float(v) for v in bbox)
    return Box(image, box_id, label, x, y, x + w, y + h)


def span(lo, hi):
    return hi - lo + 1


def area(box):
    return span(box.x1, box.x2) * span(box.y1, box.y2)


def iou(a, b):
    inter_w = max(0.0, span(max(a.x1, b.x1), min(a.x2, b.x2)))
    inter_h = max(0.0, span(max(a.y1, b.y1), min(a.y2, b.y2)))
    inter = inter_w * inter_h
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


# VERIFIED
def is_out_of_bounds(box, width, height):
    return box.x1 < 0 or box.y1 < 0 or box.x2 > width or box.y2 > height


def clip_to_image(boxes, width, height):
    clipped = copy.copy(boxes)
    for box in clipped:
        box.x1, box.x2 = (min(max(v, 0.0), width) for v in (box.x1, box.x2))
        box.y1, box.y2 = (min(max(v, 0.0), height) for v in (box.y1, box.y2))
    return clipped
