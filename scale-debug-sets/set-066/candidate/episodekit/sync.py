import bisect

SYNC_TOLERANCE_MS = 20


# VERIFIED
def nearest_offset(sorted_stamps, t):
    i = bisect.bisect_left(sorted_stamps, t)
    neighbours = sorted_stamps[max(i - 1, 0):i + 1]
    return min(abs(t - s) for s in neighbours)


def sync_ratio(camera, joints):
    """Share of camera frames that have a joint sample close enough in time."""
    if not camera or not joints:
        return 0.0
    synced = sum(1 for t in camera if nearest_offset(joints, t) < SYNC_TOLERANCE_MS)
    return round(synced / len(camera), 3)
