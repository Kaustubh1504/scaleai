from .models import EpisodeStats
from .sync import sync_ratio

MIN_FRAMES = 20
MAX_GAP_MS = 150
MIN_SYNC_RATIO = 0.9


def camera_stats(camera):
    frames = len(camera)
    if frames < 2:
        return frames, 0, None, None
    duration_ms = camera[-1] - camera[0]
    fps = round(frames / (duration_ms / 1000), 2)
    max_gap = max(b - a for a, b in zip(camera, camera[1:]))
    return frames, duration_ms, fps, max_gap


def evaluate(episode, sensors):
    camera = sensors.get("camera", [])
    joints = sensors.get("joints", [])
    frames, duration_ms, fps, max_gap = camera_stats(camera)
    stats = EpisodeStats(
        episode_id=episode.id,
        frames=frames,
        duration_ms=duration_ms,
        fps=fps,
        max_gap_ms=max_gap,
        sync_ratio=sync_ratio(camera, joints),
    )
    if not camera or not joints:
        stats.reason = "missing_stream"
    elif frames < MIN_FRAMES:
        stats.reason = "too_short"
    elif max_gap > MAX_GAP_MS:
        stats.reason = "frame_gap"
    elif stats.sync_ratio < MIN_SYNC_RATIO:
        stats.reason = "unsynced"
    else:
        stats.valid = True
    return stats


def evaluate_all(episodes, streams):
    return {ep.id: evaluate(ep, streams.get(ep.id, {})) for ep in episodes}
