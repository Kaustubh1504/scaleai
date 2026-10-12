"""23. Latest record wins (CDC stream)

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone


def parse_ts(ts: str) -> datetime:
    """ISO 8601 with "Z" or an offset -> aware UTC datetime (3.10's fromisoformat doesn't take "Z")."""
    raise NotImplementedError


def fmt_ts(dt: datetime) -> str:
    raise NotImplementedError


def materialize(events: list[dict]) -> tuple[list[dict], list[dict]]:
    # Winner per id: max by (instant, version, position). Position makes an exact tie go to the later event.
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import STREAM

    records, conflicts = materialize(STREAM)
    for r in records:
        print(r)
    print("conflicts:", conflicts)
