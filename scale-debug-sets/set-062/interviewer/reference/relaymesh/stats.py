"""Per-worker load statistics from the replay assignments."""
from __future__ import annotations

WINDOW_MS = 10_000


# VERIFIED
def sweep_points(intervals):
    """(time, delta) pairs; at equal times the -1 (finish) sorts before the +1 (start)."""
    points = []
    for start, end in intervals:
        points.append((start, 1))
        points.append((end, -1))
    return sorted(points)


def worker_stats(workers, requests, assignments) -> dict[str, dict]:
    by_worker: dict[str, list] = {w.worker_id: [] for w in workers}
    for req in requests:
        wid = assignments.get(req.request_id)
        if wid is not None:
            by_worker[wid].append(req)
    out = {}
    for wid in sorted(by_worker):
        reqs = by_worker[wid]
        busy_ms = sum(r.duration_ms for r in reqs)
        current = 0
        peak = 0
        for _, delta in sweep_points([(r.arrival_ms, r.end_ms) for r in reqs]):
            current += delta
            peak = max(peak, current)
        out[wid] = {
            "served": len(reqs),
            "busy_s": round(busy_ms / 1000, 2),
            "utilisation_pct": round(100 * busy_ms / WINDOW_MS, 1),
            "peak_inflight": peak,
        }
    return out
