import json
from dataclasses import dataclass

DEFAULTS = {"batch_size": 8, "max_concurrency": 4, "max_retries": 3, "backoff_s": 0.5, "timeout_s": 10.0}


@dataclass(frozen=True)
class Config:
    model: str
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_s: float
    timeout_s: float


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    merged = {**DEFAULTS, **raw}
    return Config(
        model=merged["model"],
        batch_size=int(merged["batch_size"]),
        max_concurrency=int(merged["max_concurrency"]),
        max_retries=int(merged["max_retries"]),
        backoff_s=float(merged["backoff_s"]),
        timeout_s=float(merged["timeout_s"]),
    )
