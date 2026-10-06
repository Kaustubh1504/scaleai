import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    min_duration_s: float
    min_sync_rate: float
    sync_tolerance_ms: int


def load_thresholds(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Thresholds(
        min_duration_s=float(raw["min_duration_s"]),
        min_sync_rate=float(raw["min_sync_rate"]),
        sync_tolerance_ms=int(raw["sync_tolerance_ms"]),
    )
