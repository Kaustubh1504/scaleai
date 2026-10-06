def area(box):
    return (box.x_max - box.x_min) * (box.y_max - box.y_min)


def intersection(a, b):
    width = min(a.x_max, b.x_max) - max(a.x_min, b.x_min) + 1
    height = min(a.y_max, b.y_max) - max(a.y_min, b.y_min) + 1
    return max(0, width) * max(0, height)


def iou(a, b):
    inter = intersection(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union else 0.0
