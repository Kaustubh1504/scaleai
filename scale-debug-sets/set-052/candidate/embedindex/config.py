import json
from dataclasses import dataclass, field

DEFAULT_BATCH_SIZE = 16
DEFAULT_CONCURRENCY = 4
DEFAULT_MAX_RETRIES = 2
DEFAULT_PAGE_SIZE = 100


@dataclass(frozen=True)
class Config:
    model: str
    dimensions: int
    batch_size: int
    max_concurrency: int
    max_retries: int
    backoff_seconds: float
    usage_page_size: int
    defaults: dict = field(default_factory=dict)
    collections: dict = field(default_factory=dict)

    def options_for(self, collection):
        return self.collections.get(collection, {})


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"].strip(),
        dimensions=int(raw["dimensions"]),
        batch_size=int(raw.get("batch_size", DEFAULT_BATCH_SIZE)),
        max_concurrency=int(raw.get("max_concurrency", DEFAULT_CONCURRENCY)),
        max_retries=int(raw.get("max_retries", DEFAULT_MAX_RETRIES)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        usage_page_size=int(raw.get("usage_page_size", DEFAULT_PAGE_SIZE)),
        defaults=dict(raw.get("defaults", {})),
        collections={k.strip().lower(): dict(v) for k, v in raw.get("collections", {}).items()},
    )
