import csv
import json

from .models import Clip, Speaker
from .normalize import clean, norm_code, norm_id, parse_flag, parse_recorded


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {
        "seed": str(raw["seed"]),
        "test_percent": int(raw["test_percent"]),
        "val_percent": int(raw["val_percent"]),
        "min_ms": int(raw["duration_ms"]["min"]),
        "max_ms": int(raw["duration_ms"]["max"]),
    }


def load_speakers(path):
    registry = {}
    for row in _read_csv(path):
        sid = norm_id(row["speaker_id"])
        registry[sid] = Speaker(id=sid, accent=clean(row["accent"]), held_out=parse_flag(row["held_out"]))
    return registry


def load_clips(path):
    clips = []
    for row in _read_csv(path):
        clips.append(Clip(
            id=norm_id(row["clip_id"]),
            speaker_id=norm_id(row["speaker_id"]),
            duration_ms=int(clean(row["duration_ms"]) or 0),
            transcript=clean(row["transcript"]),
            consent=parse_flag(row["consent"]),
            recorded_on=parse_recorded(row["recorded_on"]),
        ))
    return clips
