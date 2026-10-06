import json
from dataclasses import dataclass

DEFAULT_MAX_TOKENS = 512
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_RETRIES = 2
DEFAULT_PAGE_SIZE = 50


@dataclass(frozen=True)
class Config:
    model: str
    system_prompt: str
    max_tokens: int
    temperature: float
    max_retries: int
    backoff_seconds: float
    page_size: int


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return Config(
        model=raw["model"],
        system_prompt=raw["system_prompt"].strip(),
        max_tokens=int(raw.get("max_tokens", DEFAULT_MAX_TOKENS)),
        temperature=float(raw.get("temperature", DEFAULT_TEMPERATURE)),
        max_retries=int(raw.get("max_retries", DEFAULT_MAX_RETRIES)),
        backoff_seconds=float(raw.get("backoff_seconds", 1.0)),
        page_size=int(raw.get("page_size", DEFAULT_PAGE_SIZE)),
    )
