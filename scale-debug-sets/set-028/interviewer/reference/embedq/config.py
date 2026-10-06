import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    models: tuple
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    page_size: int


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        models=tuple(m.strip() for m in raw["models"].split(",") if m.strip()),
        batch_size=int(raw.get("batch_size", 8)),
        max_concurrency=int(raw.get("max_concurrency", 4)),
        max_retries=int(raw.get("max_retries", 2)),
        backoff_seconds=float(raw.get("backoff_seconds", 0.5)),
        page_size=int(raw.get("page_size", 50)),
    )
