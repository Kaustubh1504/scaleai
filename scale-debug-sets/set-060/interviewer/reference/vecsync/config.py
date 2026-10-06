import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Config:
    dataset: str
    model: str
    dimensions: int
    since: date
    page_size: int = 10
    batch_size: int = 8
    max_concurrency: int = 4
    max_retries: int = 2
    backoff_s: float = 0.5


def load_config(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return Config(
        dataset=raw["dataset"].strip(),
        model=raw["model"].strip(),
        dimensions=int(raw["dimensions"]),
        since=date.fromisoformat(raw["since"]),
        page_size=int(raw.get("page_size", Config.page_size)),
        batch_size=int(raw.get("batch_size", Config.batch_size)),
        max_concurrency=int(raw.get("max_concurrency", Config.max_concurrency)),
        max_retries=int(raw.get("max_retries", Config.max_retries)),
        backoff_s=float(raw.get("backoff_s", Config.backoff_s)),
    )
