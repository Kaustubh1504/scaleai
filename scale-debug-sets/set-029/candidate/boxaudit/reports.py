from collections import Counter, defaultdict
from pathlib import Path

from .loader import load_ground_truth, load_predictions
from .matching import best_iou_per_gt, match_all

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def annotator_scores(preds, gts, pairs):
    total_gt = len(gts)
    made, hits = Counter(), Counter()
    for p in preds:
        made[p.annotator] += 1
        if p.pred_id in pairs:
            hits[p.annotator] += 1
    scores = {}
    for annotator in sorted(made):
        tp = hits[annotator]
        fp = made[annotator] - tp
        fn = total_gt - tp
        scores[annotator] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(tp / (tp + fp), 3),
            "recall": round(tp / total_gt, 3),
            "f1": round(2 * tp / (2 * tp + fp + fn), 3),
        }
    return scores


def localization(gts, best):
    by_label = defaultdict(list)
    for g in gts:
        by_label[g.label].append(best[g.gt_id])
    return {label: round(sum(v) / len(v), 3) for label, v in sorted(by_label.items())}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    gts = load_ground_truth(data_dir / "ground_truth.csv")
    preds = load_predictions(data_dir / "predictions.csv")
    pairs = match_all(preds, gts)
    return {
        "matches": dict(sorted(pairs.items())),
        "annotators": annotator_scores(preds, gts, pairs),
        "localization": localization(gts, best_iou_per_gt(preds, gts)),
    }
