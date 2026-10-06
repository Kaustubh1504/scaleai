import csv
import json
from datetime import datetime

from .models import Episode, Robot

TIME_FORMATS = ("%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S")


def clean(value):
    return (value or "").strip()


def norm_episode(value):
    return clean(value).upper()


def norm_robot(value):
    return clean(value).lower()


def parse_time(value):
    text = clean(value)
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised timestamp {value!r}")


def load_robots(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    robots = {}
    for item in raw:
        rid = norm_robot(item["robot_id"])
        robots[rid] = Robot(robot_id=rid, rate_hz=float(item["rate_hz"]), active=item.get("active", True))
    return robots


def load_episodes(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            eid = norm_episode(row["episode_id"])
            if not eid:
                continue
            rows.append(Episode(
                episode_id=eid,
                robot_id=clean(row["robot_id"]),
                task=clean(row["task"]).lower(),
                operator=clean(row["operator"]),
                recorded_at=parse_time(row["recorded_at"]),
            ))
    # a re-uploaded episode replaces the earlier row (dicts keep first-seen order)
    return list({ep.episode_id: ep for ep in rows}.values())
