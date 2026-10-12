"""29. Timestamps, durations and money units

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
MS_THRESHOLD = 10**11  # 10**11 seconds is the year 5138; as milliseconds it is 1973
US_FORMATS = ("%m/%d/%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S")
UNIT_SECONDS = {"ms": Decimal("0.001"), "s": Decimal(1), "sec": Decimal(1), "m": Decimal(60), "min": Decimal(60),
                "h": Decimal(3600), "hr": Decimal(3600)}


def parse_timestamp(v: Any) -> datetime:
    raise NotImplementedError


def to_iso_z(dt: datetime) -> str:
    raise NotImplementedError


def parse_duration(v: Any) -> float:
    raise NotImplementedError


def parse_money_cents(v: Any) -> int:
    raise NotImplementedError


def local_to_utc(naive_str: str, tz_name: str) -> datetime:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import SAMPLE_ROWS

    for row in SAMPLE_ROWS:
        out = {}
        for field, fn in (("started_at", lambda r: to_iso_z(parse_timestamp(r["started_at"]))),
                          ("duration_s", lambda r: parse_duration(r["duration"])),
                          ("payout_cents", lambda r: parse_money_cents(r["payout"])),
                          ("shift_start_utc", lambda r: to_iso_z(local_to_utc(r["shift_start"], r["tz"])))):
            try:
                out[field] = fn(row)
            except ValueError as exc:
                out[field] = f"<error: {exc}>"
        print(out)
