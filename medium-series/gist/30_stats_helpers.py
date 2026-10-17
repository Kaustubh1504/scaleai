# 30. Report math: median, rates, percentiles, rollups
# Standalone: copy this file as-is. Deps: stdlib

import math
import statistics


def median(values):
    """Median ignoring None; None for no values (not 0, which would look like real data)."""
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def rate(part, whole, ndigits: int = 4, empty=0.0):
    """part / whole rounded; `empty` when whole is 0 (decide: 0.0 or None)."""
    return round(part / whole, ndigits) if whole else empty


def percentile(values, p: float):
    """Nearest-rank percentile, p in [0, 100]. None for no values."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    return vals[max(1, math.ceil(p / 100 * len(vals))) - 1]


def rollup(rows, key, fields) -> list:
    """Sum `fields` per key(row): [{"key": k, "count": n, field: total, ...}] sorted by key."""
    out = {}
    for r in rows:
        k = key(r)
        agg = out.setdefault(k, {"key": k, "count": 0, **{f: 0 for f in fields}})
        agg["count"] += 1
        for f in fields:
            agg[f] += r.get(f) or 0
    return [out[k] for k in sorted(out)]
