import json
from dataclasses import dataclass

DEFAULT_BATCH_SIZE = 16
DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_MAX_RETRIES = 2
DEFAULT_THRESHOLD = 0.9


@dataclass(frozen=True)
class Config:
    model: str
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    similarity_threshold: float


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"].strip(),
        batch_size=int(raw.get("batch_size", DEFAULT_BATCH_SIZE)),
        max_concurrency=int(raw.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)),
        max_retries=int(raw.get("max_retries", DEFAULT_MAX_RETRIES)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        similarity_threshold=float(raw.get("similarity_threshold", DEFAULT_THRESHOLD)),
    )
