from dataclasses import dataclass

from .geometry import iou

IOU_THRESHOLD = 0.5


@dataclass(frozen=True)
class Counts:
    tp: int
    fp: int
    fn: int


# VERIFIED
def pick_best(candidates):
    """candidates: (iou, gt_index). Highest IoU wins; equal IoU goes to the earlier ground-truth box."""
    return max(candidates, key=lambda c: (c[0], -c[1])) if candidates else None


def match_image(predictions, pool):
    """Greedy matching. Removes matched boxes from `pool` and returns (tp, fp)."""
    tp = fp = 0
    ordered = sorted(predictions, key=lambda p: -p[0])
    for _score, box in ordered:
        candidates = []
        for index, gt in enumerate(pool):
            if gt.label != box.label:
                continue
            overlap = iou(box, gt)
            if overlap > IOU_THRESHOLD:
                candidates.append((overlap, index))
        best = pick_best(candidates)
        if best is None:
            fp += 1
        else:
            pool.pop(best[1])
            tp += 1
    return tp, fp


def evaluate_model(predictions_by_image, ground_truth):
    """image_id -> Counts for one model, over every image."""
    # work on a copy: the same ground truth is shared by every model
    unmatched = dict(ground_truth)
    out = {}
    for image in sorted(ground_truth):
        pool = unmatched[image]
        tp, fp = match_image(predictions_by_image.get(image, []), pool)
        out[image] = Counts(tp, fp, len(pool))
    return out
