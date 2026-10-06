from .models import Verdict
from .quality import duration_ok, duration_s, has_dropped_frames
from .streams import prepare
from .sync import in_sync


def missing_streams(record, task):
    streams = record["streams"]
    return [name for name in task.required if not streams.get(name)]


def check_episode(ep, robots, tasks, frames):
    """Return a Verdict with the first rule the episode breaks (None = valid)."""
    robot = robots.get(ep.robot)
    if robot is None:
        return Verdict(ep, "unknown_robot", None)
    if ep.started_at < robot.calibrated_at:
        return Verdict(ep, "uncalibrated", None)
    task = tasks[ep.task]
    record = frames.get(ep.id, {"unit": "ms", "streams": {}})
    if missing_streams(record, task):
        return Verdict(ep, "missing_stream", None)
    camera, joints = prepare(record, robot)
    seconds = round(duration_s(camera), 2)
    if not duration_ok(seconds, task):
        return Verdict(ep, "too_short" if seconds < task.min_s else "too_long", seconds)
    if has_dropped_frames(camera, robot):
        return Verdict(ep, "dropped_frames", seconds)
    if not in_sync(camera, joints):
        return Verdict(ep, "out_of_sync", seconds)
    if ep.outcome not in ("success", "fail"):
        return Verdict(ep, "unlabelled", seconds)
    return Verdict(ep, None, seconds)
