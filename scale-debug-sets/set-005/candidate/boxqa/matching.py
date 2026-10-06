from .geometry import iou

IOU_THRESHOLD = 0.5


# VERIFIED
def greedy_match(preds, gts, threshold=IOU_THRESHOLD):
    """Return (pred_index, gt_index) pairs, best IoU first, each box used once."""
    pairs = []
    for i, p in enumerate(preds):
        for j, g in enumerate(gts):
            if p.label != g.label:
                continue
            score = iou(p, g)
            if score >= threshold:
                pairs.append((-score, i, j))
    pairs.sort()
    used_p, used_g, matches = set(), set(), []
    for _, i, j in pairs:
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j))
    return matches
