import csv
import json
from datetime import datetime

from .models import Episode, Robot, Task

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y")


def clean(value):
    return str(value if value is not None else "").strip()


def norm(value):
    return clean(value).lower()


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised time: {value!r}")


def load_robots(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    robots = {}
    for item in raw:
        rid = norm(item["id"])
        robots[rid] = Robot(
            id=rid,
            camera_hz=float(item["camera_hz"]),
            camera_offset_ms=int(item.get("camera_offset_ms") or 0),
            joint_offset_ms=int(item.get("joint_offset_ms") or 0),
            calibrated_at=parse_time(item["calibrated_at"]),
        )
    return robots


def load_tasks(path):
    tasks = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            required = tuple(norm(s) for s in clean(row["required_streams"]).split(";") if s.strip())
            tasks[norm(row["task"])] = Task(norm(row["task"]), float(row["min_s"]), float(row["max_s"]), required)
    return tasks


def load_episodes(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [Episode(
            id=clean(row["episode_id"]).upper(),
            robot=clean(row["robot_id"]),
            task=norm(row["task"]),
            operator=norm(row["operator"]),
            started_at=parse_time(row["started_at"]),
            outcome=norm(row["outcome"]),
        ) for row in csv.DictReader(fh)]


def load_frames(path):
    """episode id -> {"unit": ..., "streams": {name: [timestamps]}}"""
    frames = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            item = json.loads(line)
            frames[clean(item["episode"]).upper()] = {
                "unit": norm(item.get("unit") or "ms"),
                "streams": {norm(k): v for k, v in item.get("streams", {}).items()},
            }
    return frames
