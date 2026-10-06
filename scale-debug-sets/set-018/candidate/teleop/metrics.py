import bisect

from .models import EpisodeMetrics


def frame_times(raw):
    """Camera timestamps in ms, in time order, one per frame."""
    return sorted(raw)


# VERIFIED
def nearest_gap(sorted_ts, t):
    i = bisect.bisect_left(sorted_ts, t)
    candidates = sorted_ts[max(i - 1, 0):i + 1]
    return min(abs(t - c) for c in candidates) if candidates else None


def sync_rate(frames, joints, tolerance_ms):
    if not frames:
        return 0.0
    joints = sorted(joints)
    matched = 0
    for t in frames:
        gap = nearest_gap(joints, t)
        if gap is not None and gap < tolerance_ms:
            matched += 1
    return round(matched / len(frames), 3)


def compute_metrics(episode, thresholds):
    frames = frame_times(episode.camera_ms)
    span_ms = frames[-1] - frames[0] if frames else 0
    gaps = [b - a for a, b in zip(frames, frames[1:])]
    return EpisodeMetrics(
        frames=len(frames),
        span_ms=span_ms,
        duration_s=round(span_ms // 1000, 2),
        max_gap_ms=max(gaps, default=0),
        sync_rate=sync_rate(frames, episode.joints_ms, thresholds.sync_tolerance_ms),
    )
