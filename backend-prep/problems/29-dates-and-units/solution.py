"""29. Timestamps, durations and money units: reference solution."""

import math
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

UTC = timezone.utc
UNIT_SECONDS = {"ms": Decimal("0.001"), "s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600, "hr": 3600}
PART = r"(\d+(?:\.\d+)?)\s*(ms|sec|min|hr|s|m|h)"


def parse_timestamp(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise ValueError(f"not a timestamp: {v!r}")
    s = str(v).strip()  # str() keeps a float like 0.25 exact
    if isinstance(v, (int, float)) or re.fullmatch(r"-?\d+(\.\d+)?", s):
        n = Decimal(s)
        if not n.is_finite():
            raise ValueError(f"not a timestamp: {v!r}")
        if abs(n) >= 10**11:  # milliseconds
            n /= 1000
        try:
            return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=round(n * 10**6))
        except OverflowError:
            raise ValueError(f"timestamp out of range: {v!r}") from None
    if "/" in s:
        for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=UTC)
            except ValueError:
                pass
        raise ValueError(f"not a US date: {v!r}")
    return parse_timestamp(datetime.fromisoformat(s.upper()))  # fromisoformat rejects a lowercase z


def to_iso_z(dt: datetime) -> str:
    if dt.utcoffset() is None:
        raise ValueError("refusing to format a naive datetime")
    dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.isoformat(timespec="microseconds" if dt.microsecond else "seconds") + "Z"


def parse_duration(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise ValueError(f"not a duration: {v!r}")
    if not isinstance(v, str):
        if not math.isfinite(v) or v < 0:
            raise ValueError(f"not a duration: {v!r}")
        return float(v)
    s = v.strip().lower()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    if m := re.fullmatch(r"(\d+):([0-5]\d)(?::([0-5]\d(?:\.\d+)?))?", s):
        first, second, third = m.groups()
        if third is None:  # MM:SS
            return int(first) * 60 + float(second)
        return int(first) * 3600 + int(second) * 60 + float(third)
    if re.fullmatch(rf"(?:{PART}\s*)+", s):
        return float(sum(Decimal(n) * UNIT_SECONDS[unit] for n, unit in re.findall(PART, s)))
    raise ValueError(f"not a duration: {v!r}")


def parse_money_cents(v: Any) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float, Decimal, str)):
        raise ValueError(f"not an amount: {v!r}")
    if isinstance(v, str):
        s = v.strip().lower()
        if m := re.fullmatch(r"(-?\d+)\s*(?:c|cents|¢)", s):
            return int(m[1])
        s = s.removeprefix("usd").removesuffix("usd").strip()
        if not re.fullmatch(r"-?\$?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?", s):
            raise ValueError(f"not an amount: {v!r}")
        dollars = Decimal(s.replace("$", "").replace(",", ""))
    else:
        dollars = Decimal(str(v))  # str(): int(19.99 * 100) would be 1998
    cents = dollars * 100
    if not cents.is_finite() or cents != cents.to_integral_value():
        raise ValueError(f"not a whole number of cents: {v!r}")
    return int(cents)


def local_to_utc(naive_str: str, tz_name: str) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except (KeyError, ValueError):  # ZoneInfoNotFoundError is a KeyError
        raise ValueError(f"unknown timezone: {tz_name!r}") from None
    wall = datetime.fromisoformat(naive_str.strip())
    if wall.tzinfo is not None:
        raise ValueError(f"expected a naive local time: {naive_str!r}")
    utc = wall.replace(tzinfo=tz).astimezone(UTC)  # fold=0 picks the earlier of a repeated time
    if utc.astimezone(tz).replace(tzinfo=None) != wall:  # no round trip means a DST gap
        raise ValueError(f"{naive_str!r} does not exist in {tz_name}")
    return utc


if __name__ == "__main__":
    from problem_api import SAMPLE_ROWS

    for row in SAMPLE_ROWS:
        for fn, arg in [(parse_timestamp, row["started_at"]), (parse_duration, row["duration"]),
                        (parse_money_cents, row["payout"])]:
            try:
                print(repr(fn(arg)), end="  ")
            except ValueError as exc:
                print("<error>", exc, end="  ")
        print()
