import csv
import json
from datetime import datetime

from .models import Episode, Robot

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y")
TRUTHY = {"true", "yes", "y", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def norm_id(value):
    return clean(value).upper()


def parse_bool(value):
    text = clean(value)
    if not text:
        return True
    return bool(text)


def parse_date(value):
    text = clean(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r}")


def load_robots(path):
    robots = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            robot = Robot(norm_id(row["robot_id"]), clean(row["model"]),
                          int(clean(row["max_gap_ms"])), parse_bool(row["active"]))
            robots[robot.robot_id] = robot
    return robots


def load_episodes(csv_path, frames_path):
    with open(frames_path, encoding="utf-8") as fh:
        streams = {norm_id(e["episode_id"]): e for e in json.load(fh)["episodes"]}
    episodes = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            eid = norm_id(row["episode_id"])
            stream = streams.get(eid, {})
            episodes.append(Episode(
                episode_id=eid,
                robot_id=norm_id(row["robot_id"]),
                operator=clean(row["operator"]).lower(),
                task=clean(row["task"]).lower(),
                recorded_on=parse_date(row["recorded_on"]),
                success=clean(row["success"]).lower() in TRUTHY,
                camera_ms=[int(t) for t in stream.get("camera_ms", [])],
                joints_ms=[int(t) for t in stream.get("joints_ms", [])],
            ))
    return episodes
