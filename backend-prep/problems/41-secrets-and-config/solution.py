"""41. Secrets and config from the environment: reference solution."""

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
        return (f"Settings(api_key='***', base_url={self.base_url!r}, timeout_s={self.timeout_s!r}, "
                f"max_retries={self.max_retries!r}, log_level={self.log_level!r})")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        api_key = env.get("API_KEY", "").strip()
        base_url = env.get("BASE_URL", "").strip().rstrip("/")
        timeout = env.get("TIMEOUT_S", "").strip() or "10"
        retries = env.get("MAX_RETRIES", "").strip() or "3"
        log_level = (env.get("LOG_LEVEL", "").strip() or "INFO").upper()

        problems = []
        if not api_key:
            problems.append("API_KEY is required")
        if not base_url.startswith("https://"):
            problems.append(f"BASE_URL is required and must start with https:// (got {base_url!r})")
        try:
            timeout_s = float(timeout)
        except ValueError:
            timeout_s = 0.0
        if not (math.isfinite(timeout_s) and timeout_s > 0):
            problems.append(f"TIMEOUT_S must be a finite number > 0 (got {timeout!r})")
        max_retries = int(retries) if retries.isdecimal() else -1
        if max_retries < 0:
            problems.append(f"MAX_RETRIES must be an integer >= 0 (got {retries!r})")
        if log_level not in LOG_LEVELS:
            problems.append(f"LOG_LEVEL must be one of {', '.join(LOG_LEVELS)} (got {log_level!r})")

        if problems:
            raise ConfigError(problems)
        return cls(api_key, base_url, timeout_s, max_retries, log_level)


def load_dotenv(path: str | Path) -> dict[str, str]:
    values = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip().removeprefix("export ")
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_settings(dotenv_path: str | Path | None = None,
                  env: Mapping[str, str] | None = None) -> Settings:
    dotenv = load_dotenv(dotenv_path) if dotenv_path and Path(dotenv_path).exists() else {}
    return Settings.from_env({**dotenv, **(os.environ if env is None else env)})


if __name__ == "__main__":
    print(Settings.from_env({"API_KEY": "sk_live_abc", "BASE_URL": "https://api.scale.test/",
                             "LOG_LEVEL": "debug"}))
    try:
        Settings.from_env({"BASE_URL": "http://x", "TIMEOUT_S": "0"})
    except ConfigError as exc:
        print("ConfigError:", exc)
