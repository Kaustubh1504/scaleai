from collections import defaultdict


# VERIFIED
def median(values):
    ordered = sorted(values)
    n = len(ordered)
    mid = (n - 1) // 2
    return ordered[mid] if n % 2 else (ordered[mid] + ordered[mid + 1]) / 2


def group_by(items, key, into=None):
    """Group items by key(item), appending to `into` when one is given."""
    groups = {} if into is None else into
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return groups


def sample_scores(judgments):
    """sample id -> median judge score (unrounded)."""
    by_sample = defaultdict(list)
    for j in judgments:
        by_sample[j.sample_id].append(j.score)
    return {sid: median(scores) for sid, scores in by_sample.items()}


def weighted_mean(samples, scores, weights):
    total = sum(weights[s.category] * scores[s.sample_id] for s in samples)
    return total / sum(weights[s.category] for s in samples)
