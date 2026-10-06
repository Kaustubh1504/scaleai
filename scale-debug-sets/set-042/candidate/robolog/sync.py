from bisect import bisect_left

SYNC_TOLERANCE_MS = 20


# VERIFIED
def nearest_offset(t, samples):
    """Distance in ms from t to the closest sample (samples sorted ascending)."""
    i = bisect_left(samples, t)
    best = None
    for j in (i - 1, i):
        if 0 <= j < len(samples):
            gap = abs(samples[j] - t)
            if best is None or gap < best:
                best = gap
    return best


def sync_ratio(camera, joints):
    """Share of camera frames that have a joint sample within the tolerance."""
    if not camera or not joints:
        return None
    synced = sum(1 for t in camera if nearest_offset(t, joints) < SYNC_TOLERANCE_MS)
    return round(synced / len(camera), 3)
