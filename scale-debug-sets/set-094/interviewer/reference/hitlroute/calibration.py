from collections import Counter, defaultdict
from itertools import groupby


def _model(review):
    return review.model


def model_calibration(reviews):
    table = {}
    for model, group in groupby(sorted(reviews, key=_model), key=_model):
        rows = list(group)
        agreement = sum(r.model_label == r.human_label for r in rows) / len(rows)
        mean_conf = sum(r.confidence for r in rows) / len(rows)
        table[model] = {
            "reviews": len(rows),
            "agreement": round(agreement, 3),
            "mean_confidence": round(mean_conf, 3),
            "gap": round(mean_conf - agreement, 3),
        }
    return dict(sorted(table.items()))


def label_confusions(reviews):
    confusions = defaultdict(Counter)
    for r in reviews:
        counts = confusions[r.model_label]
        if r.model_label != r.human_label:
            counts[r.human_label] += 1
    result = {}
    for label, counts in sorted(confusions.items()):
        result[label] = min(counts, key=lambda h: (-counts[h], h)) if counts else None
    return result
