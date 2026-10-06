import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    model: str
    batch_size: int
    page_size: int
    max_concurrency: int
    max_retries: int
    backoff_s: float
    poll_interval_s: float

    @property
    def max_attempts(self):
        return self.max_retries


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"],
        batch_size=int(raw["batch_size"]),
        page_size=int(raw["page_size"]),
        max_concurrency=int(raw["max_concurrency"]),
        max_retries=int(raw["max_retries"]),
        backoff_s=float(raw["backoff_s"]),
        poll_interval_s=float(raw["poll_interval_s"]),
    )
