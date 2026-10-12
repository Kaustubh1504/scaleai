"""41. Secrets and config from the environment

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__(f"{len(problems)} config problem(s): " + "; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    timeout_s: float = 10.0
    max_retries: int = 3
    log_level: str = "INFO"

    def __repr__(self) -> str:
        raise NotImplementedError

    __str__ = __repr__

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        raise NotImplementedError


def load_dotenv(path: str | Path) -> dict[str, str]:
    raise NotImplementedError


def load_settings(dotenv_path: str | Path | None = None, env: Mapping[str, str] | None = None) -> Settings:
    raise NotImplementedError


if __name__ == "__main__":
    s = Settings.from_env({"API_KEY": "sk_live_abc", "BASE_URL": "https://api.scale.test/", "LOG_LEVEL": "debug"})
    print(s)
    try:
        Settings.from_env({"BASE_URL": "http://x", "TIMEOUT_S": "0"})
    except ConfigError as exc:
        print("ConfigError:", exc)
