from collections import defaultdict

from .aggregate import median
from .calibration import adjust, bias_for
from .models import Result


def resolve(items, ratings, gold, memo, config):
    by_item = defaultdict(list)
    for r in ratings:
        by_item[r.item_id].append(r)

    results = {}
    within = 0
    for item in items.values():
        if item.gold is not None:
            continue
        votes = [adjust(r.score, bias_for(memo, gold, items, r.annotator_id, item.rubric))
                 for r in by_item.get(item.id, [])]
        if len(votes) < config["min_votes"]:
            results[item.id] = Result(item.id, item.rubric, "insufficient", None, None, len(votes))
            continue
        center = median(votes)
        for v in votes:
            if abs(v - center) <= config["tolerance"]:
                within += 1
        agreement = round(within / len(votes), 3)
        status = "contested" if agreement < config["contested_below"] else "agreed"
        results[item.id] = Result(item.id, item.rubric, status, round(center, 3), agreement, len(votes))
    return results
