import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    model: str
    max_concurrency: int
    max_retries: int
    max_polls: int
    poll_interval_s: float
    page_size: int
    review_threshold: float
    price_per_1k_tokens: float


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"],
        max_concurrency=int(raw.get("max_concurrency", 4)),
        max_retries=int(raw.get("max_retries", 2)),
        max_polls=int(raw.get("max_polls", 20)),
        poll_interval_s=float(raw.get("poll_interval_s", 1.0)),
        page_size=int(raw.get("page_size", 50)),
        review_threshold=float(raw["review_threshold"]),
        price_per_1k_tokens=float(raw["price_per_1k_tokens"]),
    )
