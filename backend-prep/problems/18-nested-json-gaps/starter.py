"""18. Nested JSON with gaps

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from typing import Any, Callable, Optional


def get_path(obj: Any, path: str, default: Any = None) -> Any:
    raise NotImplementedError


def to_profile(record: dict) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import RECORDS

    for rec in RECORDS:
        print(to_profile(rec))
