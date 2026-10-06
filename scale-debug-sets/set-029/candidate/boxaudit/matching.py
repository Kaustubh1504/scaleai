from collections import defaultdict

from .geometry import iou

THRESHOLDS = {"person": 0.5, "car": 0.6, "sign": 0.7}


def candidates(preds, gts):
    found = []
    for p in preds:
        for g in gts:
            if p.label != g.label or p.label not in THRESHOLDS:
                continue
            value = iou(p.box, g.box)
            if value >= THRESHOLDS[p.label]:
                found.append((value, p.pred_id, g.gt_id))
    return found


def match(preds, gts):
    """Greedy one-to-one matching, best overlap first. Returns {pred_id: gt_id}."""
    pairs, used_gt = {}, set()
    for value, pid, gid in sorted(candidates(preds, gts), key=lambda c: c[0]):
        if pid in pairs or gid in used_gt:
            continue
        pairs[pid] = gid
        used_gt.add(gid)
    return pairs


def match_all(preds, gts):
    gts_by_image = defaultdict(list)
    for g in gts:
        gts_by_image[g.image_id].append(g)
    groups = defaultdict(list)
    for p in preds:
        groups[(p.image_id, p.annotator)].append(p)
    pairs = {}
    for (image_id, _), group in sorted(groups.items()):
        pairs.update(match(group, gts_by_image.get(image_id, [])))
    return pairs


# VERIFIED
def best_iou_per_gt(preds, gts):
    """For each ground-truth box, the best IoU from any annotator's same-label prediction."""
    best = {}
    for g in gts:
        scores = [iou(p.box, g.box) for p in preds if p.image_id == g.image_id and p.label == g.label]
        best[g.gt_id] = max(scores, default=0.0)
    return best
