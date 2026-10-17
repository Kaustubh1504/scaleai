# 47. Bounding-box IoU and matching
# Standalone: copy this file as-is. Deps: stdlib

def xywh_to_xyxy(box):
    x, y, w, h = box
    return (x, y, x + w, y + h)


def iou(a, b) -> float:
    """Boxes as (x1, y1, x2, y2). 0.0 when they don't overlap or have zero area."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def match_boxes(preds, golds, threshold: float = 0.5):
    """Greedy one-to-one matching, best IoU first. Returns (matches [(pred_i, gold_i, iou)],
    unmatched_pred_indexes, unmatched_gold_indexes). precision = matches/len(preds), recall = matches/len(golds)."""
    pairs = sorted(((iou(p, g), i, j) for i, p in enumerate(preds) for j, g in enumerate(golds)),
                   key=lambda t: (-t[0], t[1], t[2]))
    used_p, used_g, matches = set(), set(), []
    for score, i, j in pairs:
        if score < threshold:
            break
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        matches.append((i, j, round(score, 4)))
    return (matches, [i for i in range(len(preds)) if i not in used_p],
            [j for j in range(len(golds)) if j not in used_g])
