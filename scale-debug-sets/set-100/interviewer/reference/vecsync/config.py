import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    model: str
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    index_page_size: int


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"].strip(),
        batch_size=int(raw.get("batch_size", 8)),
        max_concurrency=int(raw.get("max_concurrency", 4)),
        max_retries=int(raw.get("max_retries", 3)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        index_page_size=int(raw.get("index_page_size", 100)),
    )
