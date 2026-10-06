import csv
import json
from pathlib import Path

from .models import Episode
from .utils import clean, norm_episode, parse_bool, parse_timestamp

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def split_tags(raw):
    text = clean(raw).lower()
    return [tag.strip() for tag in text.split(";")] if text else []


def load_episodes(path=None):
    episodes = []
    with open(path or DATA_DIR / "episodes.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            episodes.append(Episode(
                id=norm_episode(row["episode_id"]),
                robot=clean(row["robot"]).lower(),
                operator=clean(row["operator"]).lower(),
                task=clean(row["task"]).lower(),
                recorded_at=parse_timestamp(row["recorded_at"]),
                tags=split_tags(row["tags"]),
                success=parse_bool(row["success"]),
            ))
    return episodes


def load_streams(path=None):
    """{episode_id: {sensor: sorted timestamps in ms}}"""
    with open(path or DATA_DIR / "streams.json", encoding="utf-8") as fh:
        raw = json.load(fh)
    streams = {}
    for item in raw:
        sensors = streams.setdefault(norm_episode(item["episode"]), {})
        sensors[clean(item["sensor"]).lower()] = sorted(int(t) for t in item["t_ms"])
    return streams
