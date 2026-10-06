import json

from .loader import clean, norm_episode
from .models import Stream

SENSORS = ("camera", "joints")


# VERIFIED
def to_ms(value, unit):
    if unit == "s":
        return round(value * 1000)
    return round(value)


def load_streams(path):
    """Return {(episode_id, sensor): Stream} for the sensors we validate."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    streams = {}
    for rec in raw:
        sensor = clean(rec.get("sensor")).lower()
        if sensor not in SENSORS:
            continue
        unit = clean(rec.get("unit")).lower() or "ms"
        eid = norm_episode(rec["episode"])
        stamps = sorted({to_ms(t, unit) for t in rec["t"]})
        streams[(eid, sensor)] = Stream(episode_id=eid, sensor=sensor, timestamps_ms=stamps)
    return streams


def camera_stats(stamps):
    gaps = [later - earlier for earlier, later in zip(stamps, stamps[1:])]
    return {
        "frames": len(stamps),
        "duration_ms": stamps[-1] - stamps[0] if stamps else 0,
        "max_gap_ms": max(gaps, default=0),
    }
