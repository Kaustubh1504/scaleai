from collections import defaultdict

from .models import ItemResult, Status

OUTLIER_GAP = 3
MIN_RATINGS = 3
AGREEMENT_BAR = 0.6


def median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def drop_outliers(ratings):
    centre = median(r.rating for r in ratings)
    kept, outliers = list(ratings), []
    for r in list(kept):
        if abs(r.rating - centre) > OUTLIER_GAP:
            kept.remove(r)
            outliers.append(r)
    return kept, outliers


# VERIFIED
def agreement(values, centre):
    close = sum(1 for v in values if abs(v - centre) <= 1)
    return round(close / len(values), 3)


def score_items(items, ratings):
    by_item = defaultdict(list)
    for r in ratings:
        by_item[r.item_id].append(r)
    results, outliers = {}, []
    for iid in sorted(items):
        item, rows = items[iid], by_item.get(iid, [])
        if item.adjudicated is not None:
            results[iid] = ItemResult(iid, Status.ADJUDICATED, item.adjudicated, None)
            continue
        if len(rows) < MIN_RATINGS:
            results[iid] = ItemResult(iid, Status.INSUFFICIENT, None, None)
            continue
        kept, dropped = drop_outliers(rows)
        outliers.extend(dropped)
        values = [r.rating for r in kept]
        centre = median(values)
        share = agreement(values, centre)
        status = Status.AGREED if share >= AGREEMENT_BAR else Status.ESCALATED
        results[iid] = ItemResult(iid, status, centre, share)
    return results, outliers
