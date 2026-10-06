import math


def p50(values):
    """Nearest-rank median."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.5 * len(ordered)) - 1]


def per_backend(assignments, requests, backends):
    durations = {bid: [] for bid in backends}
    for req in requests:
        bid = assignments.get(req.id)
        if bid is not None:
            durations[bid].append(req.duration_ms)
    return {bid: {"requests": len(vals), "p50_ms": p50(vals)} for bid, vals in sorted(durations.items())}
