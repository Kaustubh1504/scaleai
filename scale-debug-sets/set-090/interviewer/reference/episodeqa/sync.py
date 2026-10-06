from bisect import bisect_left

TOLERANCE_MS = 25
MIN_SYNC_RATIO = 0.9


# VERIFIED
def nearest_gap(sorted_ts, t):
    """Distance from t to the closest value in sorted_ts."""
    i = bisect_left(sorted_ts, t)
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(sorted_ts):
            gap = abs(sorted_ts[j] - t)
            best = gap if best is None else min(best, gap)
    return best


def sync_ratio(camera, joints):
    if not camera or not joints:
        return 0.0
    synced = sum(1 for t in camera if nearest_gap(joints, t) <= TOLERANCE_MS)
    return synced / len(camera)


def in_sync(camera, joints):
    return sync_ratio(camera, joints) >= MIN_SYNC_RATIO
