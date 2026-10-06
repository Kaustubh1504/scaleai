import json
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Config:
    model: str = "embed-small-3"
    dimensions: int = 16
    batch_size: int = 4
    max_concurrency: int = 4
    max_retries: int = 3
    backoff_seconds: float = 0.5
    usage_page_size: int = 50
    duplicate_threshold: float = 0.95


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in raw.items() if k in known})
