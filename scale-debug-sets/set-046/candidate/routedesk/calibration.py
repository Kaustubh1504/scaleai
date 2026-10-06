from collections import Counter, defaultdict


def agreement_rates(reviews):
    totals = Counter(r.model_label for r in reviews)
    agreed = Counter(r.model_label for r in reviews if r.human_label == r.model_label)
    return {label: round(agreed[label] / totals[label], 3) for label in sorted(totals)}


def reviewer_mix(reviews):
    mix = defaultdict(Counter)
    for r in reviews:
        mix[r.reviewer_id].update(r.human_label)
    return {rid: dict(sorted(mix[rid].items())) for rid in sorted(mix)}


def calibrate(reviews):
    usable = [r for r in reviews if r.human_label]
    return {
        "agreement": agreement_rates(usable),
        "reviewer_mix": reviewer_mix(usable),
        "last_review_at": max(r.finished_at for r in usable) if usable else None,
    }
