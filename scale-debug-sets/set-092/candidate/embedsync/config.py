import json
from dataclasses import dataclass
from datetime import date

DEFAULTS = {
    "model": "embed-small-1",
    "dimensions": 2,
    "batch_size": 4,
    "max_concurrency": 4,
    "max_retries": 3,
    "backoff_seconds": 1.0,
    "page_size": 10,
    "price_per_1k_tokens": 0.1,
}


@dataclass
class Config:
    model: str
    dimensions: int
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    page_size: int
    price_per_1k_tokens: float
    as_of: date


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    values = {key: raw.get(key, default) for key, default in DEFAULTS.items()}
    values["as_of"] = date.fromisoformat(raw["as_of"])
    return Config(**values)
