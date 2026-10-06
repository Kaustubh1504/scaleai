import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    workers: int
    default_max_retries: int


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        workers=int(raw.get("workers", 1)),
        default_max_retries=int(raw.get("default_max_retries", 0)),
    )
