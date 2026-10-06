from collections import Counter
from pathlib import Path

from .loader import load_episodes, load_robots
from .streams import camera_stats, load_streams
from .validity import check_episode

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(results):
    valid = [r for r in results if r.valid]
    by_task = Counter(r.task for r in valid)
    by_day = Counter(r.recorded_at.date().isoformat() for r in valid)
    reasons = Counter()
    for r in results:
        if not r.valid:
            reasons.update(r.reason)
    ratios = [r.sync_ratio for r in valid]
    return {
        "total": len(results),
        "valid": len(valid),
        "valid_by_task": dict(sorted(by_task.items())),
        "valid_by_day": dict(sorted(by_day.items())),
        "invalid_reasons": dict(sorted(reasons.items())),
        "mean_sync_ratio": round(sum(ratios) / len(ratios), 3) if ratios else None,
        "valid_duration_s": round(sum(r.duration_ms for r in valid) / 1000, 1),
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    robots = load_robots(data_dir / "robots.json")
    episodes = load_episodes(data_dir / "episodes.csv")
    streams = load_streams(data_dir / "streams.json")
    results = [check_episode(ep, robots, streams) for ep in episodes]
    return {
        "episode_ids": [ep.episode_id for ep in episodes],
        "camera": {ep.episode_id: camera_stats(streams[(ep.episode_id, "camera")].timestamps_ms)
                   for ep in episodes if (ep.episode_id, "camera") in streams},
        "joint_samples": {ep.episode_id: len(streams[(ep.episode_id, "joints")].timestamps_ms)
                          for ep in episodes if (ep.episode_id, "joints") in streams},
        "episodes": {r.episode_id: {"valid": r.valid, "reason": r.reason} for r in results},
        "summary": summarize(results),
    }
