import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEFAULTS = {
    "batch_size": 16,
    "max_concurrency": 4,
    "max_retries": 3,
    "backoff_seconds": 0.5,
    "index_page_size": 50,
}


@dataclass(frozen=True)
class Config:
    model: str
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    index_page_size: int


def load_config(path=None):
    with open(path or DATA_DIR / "config.json", encoding="utf-8") as fh:
        raw = json.load(fh)
    merged = {**DEFAULTS, **raw}
    return Config(**{k: merged[k] for k in Config.__dataclass_fields__})
