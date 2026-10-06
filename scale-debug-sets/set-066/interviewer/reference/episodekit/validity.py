from .models import EpisodeResult
from .streams import camera_stats
from .sync import sync_ratio

MIN_FRAMES = 6
MIN_SYNC_RATIO = 0.8
GAP_FACTOR = 2


def max_gap_allowed(robot):
    period_ms = 1000 / robot.rate_hz
    return GAP_FACTOR * period_ms


def check_episode(episode, robots, streams):
    robot = robots.get(episode.robot_id)
    camera = streams.get((episode.episode_id, "camera"))
    joints = streams.get((episode.episode_id, "joints"))
    stats = camera_stats(camera.timestamps_ms if camera else [])

    def result(reason, ratio=None):
        return EpisodeResult(
            episode_id=episode.episode_id, task=episode.task, recorded_at=episode.recorded_at,
            valid=reason is None, reason=reason, duration_ms=stats["duration_ms"], sync_ratio=ratio,
        )

    if robot is None or not robot.active:
        return result("robot_unavailable")
    if camera is None or joints is None:
        return result("missing_stream")
    if stats["frames"] < MIN_FRAMES:
        return result("too_short")
    if stats["max_gap_ms"] > max_gap_allowed(robot):
        return result("frame_gap")
    ratio = sync_ratio(camera.timestamps_ms, joints.timestamps_ms)
    if ratio < MIN_SYNC_RATIO:
        return result("desync", ratio)
    return result(None, ratio)
