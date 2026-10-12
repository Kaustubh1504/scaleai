from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

UTC = timezone.utc


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def test_iso_timestamps(sol):
    """parse_timestamp handles ISO with Z, offsets, naive (UTC), space separator and date-only"""
    cases = {
        "2024-03-01T10:00:00Z": utc(2024, 3, 1, 10),
        " 2024-03-01T10:00:00z ": utc(2024, 3, 1, 10),
        "2024-03-01T12:00:00+05:30": utc(2024, 3, 1, 6, 30),
        "2024-03-01T01:00:00-08:00": utc(2024, 3, 1, 9),
        "2024-03-01T10:00:00": utc(2024, 3, 1, 10),
        "2024-03-01 10:00": utc(2024, 3, 1, 10),
        "2024-03-01": utc(2024, 3, 1),
        "2024-03-01T10:00:00.250Z": utc(2024, 3, 1, 10, 0, 0, 250000),
    }
    for raw, want in cases.items():
        got = sol.parse_timestamp(raw)
        assert got.tzinfo is not None and got.utcoffset() == timedelta(0), f"{raw!r}: result must be aware UTC"
        assert got == want, f"parse_timestamp({raw!r}) = {got!r}, expected {want!r}"


def test_us_dates_and_datetimes(sol):
    """parse_timestamp reads MM/DD/YYYY [HH:MM[:SS]] as US dates in UTC and accepts datetime objects"""
    assert sol.parse_timestamp("03/01/2024") == utc(2024, 3, 1)
    assert sol.parse_timestamp("03/01/2024 14:15") == utc(2024, 3, 1, 14, 15), "MM/DD, not DD/MM"
    assert sol.parse_timestamp("12/31/2023 23:59:59") == utc(2023, 12, 31, 23, 59, 59)
    assert sol.parse_timestamp(datetime(2024, 3, 1, 10)) == utc(2024, 3, 1, 10), "naive datetime means UTC"
    eastern = timezone(timedelta(hours=-5))
    got = sol.parse_timestamp(datetime(2024, 3, 1, 5, tzinfo=eastern))
    assert got == utc(2024, 3, 1, 10) and got.utcoffset() == timedelta(0), "aware datetimes are converted to UTC"


def test_epoch_seconds_and_millis(sol):
    """parse_timestamp reads epoch seconds and milliseconds (>= 10**11) from ints, floats and strings exactly"""
    base = utc(2024, 3, 1, 11)
    assert sol.parse_timestamp(1709290800) == base
    assert sol.parse_timestamp("1709290800") == base
    assert sol.parse_timestamp(1709290800123) == base + timedelta(milliseconds=123), "13 digits = milliseconds"
    assert sol.parse_timestamp("1709290800123") == base + timedelta(milliseconds=123)
    assert sol.parse_timestamp("1709290800.5") == base + timedelta(microseconds=500000)
    assert sol.parse_timestamp(1709290800.25) == base + timedelta(microseconds=250000)
    assert sol.parse_timestamp(0) == utc(1970, 1, 1)


def test_bad_timestamps(sol):
    """parse_timestamp raises ValueError for junk, impossible US dates, bools and NaN"""
    for raw in ("", "yesterday", "13/01/2024", "2024-02-30", "03-01-2024 10am", True, float("nan"), None):
        with pytest.raises(ValueError):
            sol.parse_timestamp(raw)
            pytest.fail(f"parse_timestamp({raw!r}) should raise ValueError")


def test_to_iso_z(sol):
    """to_iso_z formats UTC with a Z, adds .ffffff only when needed, and rejects naive datetimes"""
    assert sol.to_iso_z(utc(2024, 3, 1, 11)) == "2024-03-01T11:00:00Z"
    assert sol.to_iso_z(utc(2024, 3, 1, 11, 0, 0, 123000)) == "2024-03-01T11:00:00.123000Z"
    plus2 = timezone(timedelta(hours=2))
    assert sol.to_iso_z(datetime(2024, 3, 1, 1, 30, tzinfo=plus2)) == "2024-02-29T23:30:00Z", "convert to UTC first"
    with pytest.raises(ValueError):
        sol.to_iso_z(datetime(2024, 3, 1, 11))
        pytest.fail("a naive datetime must be rejected, not assumed")


def test_durations(sol):
    """parse_duration handles bare numbers, unit suffixes, compound parts and clock formats"""
    cases = {
        45: 45.0, 2.5: 2.5, "45": 45.0, "2.5": 2.5, "90s": 90.0, "90 sec": 90.0, "1.5m": 90.0,
        "2min": 120.0, "2h": 7200.0, " 2 HR ": 7200.0, "1500ms": 1.5, "1h30m": 5400.0, "2m 30s": 150.0,
        "1h 0m 1s": 3601.0, "01:30:00": 5400.0, "1:30": 90.0, "100:00:00": 360000.0, "00:00:01.5": 1.5,
    }
    for raw, want in cases.items():
        got = sol.parse_duration(raw)
        assert isinstance(got, float), f"parse_duration({raw!r}) must return a float"
        assert got == pytest.approx(want), f"parse_duration({raw!r}) = {got!r}, expected {want}"


def test_bad_durations(sol):
    """parse_duration raises ValueError for negatives, unknown units, bad clocks and junk"""
    for raw in ("-5s", -1, "5x", "1:75", "1:30:75", "h", "", "abc", "1h-30m", True, float("inf")):
        with pytest.raises(ValueError):
            sol.parse_duration(raw)
            pytest.fail(f"parse_duration({raw!r}) should raise ValueError")


def test_money_cents(sol):
    """parse_money_cents converts dollars and cents forms to exact integer cents"""
    cases = {
        "$12.30": 1230, "12.30": 1230, "12.3": 1230, "12": 1200, 12: 1200, " $1,000.00 ": 100000,
        "-$5.00": -500, "USD 12.30": 1230, "12.30 usd": 1230, "1230c": 1230, "1230 cents": 1230,
        "1230¢": 1230, "-120c": -120, Decimal("0.5"): 50, "12.300": 1230,
    }
    for raw, want in cases.items():
        got = sol.parse_money_cents(raw)
        assert type(got) is int, f"parse_money_cents({raw!r}) must return an int"
        assert got == want, f"parse_money_cents({raw!r}) = {got!r}, expected {want}"


def test_money_never_float_rounds(sol):
    """parse_money_cents(19.99) is 1999 (not 1998) and fractional cents raise ValueError"""
    assert sol.parse_money_cents(19.99) == 1999, "int(19.99 * 100) == 1998: go through Decimal(str(v))"
    assert sol.parse_money_cents(0.07) == 7
    for raw in ("$12.345", 0.1 + 0.2, "12.5c", "$", "12,34", "twelve", True, "$-5"):
        with pytest.raises(ValueError):
            sol.parse_money_cents(raw)
            pytest.fail(f"parse_money_cents({raw!r}) should raise ValueError")


def test_local_to_utc(sol):
    """local_to_utc converts wall-clock times in IANA zones, including half-hour offsets and DST"""
    assert sol.local_to_utc("2024-07-01 09:00", "America/Los_Angeles") == utc(2024, 7, 1, 16), "PDT is UTC-7"
    assert sol.local_to_utc("2024-01-15 09:00", "America/Los_Angeles") == utc(2024, 1, 15, 17), "PST is UTC-8"
    assert sol.local_to_utc("2024-07-01 09:00", "Asia/Kolkata") == utc(2024, 7, 1, 3, 30)
    assert sol.local_to_utc("2024-03-31 00:30:00", "Europe/London") == utc(2024, 3, 31, 0, 30), "still GMT"
    assert sol.local_to_utc("2024-03-31 03:30", "Europe/London") == utc(2024, 3, 31, 2, 30), "now BST (UTC+1)"
    got = sol.local_to_utc("2024-11-03 01:30", "America/New_York")
    assert got == utc(2024, 11, 3, 5, 30), "a repeated (fall-back) time resolves to the earlier instant (EDT)"
    assert got.utcoffset() == timedelta(0), "the result must be in UTC"


def test_local_to_utc_errors(sol):
    """local_to_utc raises ValueError for a DST-gap time, an unknown zone, an offset or junk"""
    bad = [("2024-03-10 02:30", "America/New_York"), ("2024-03-31 01:30", "Europe/London"), ("2024-03-31 02:30", "Europe/Berlin"),
           ("2024-07-01 09:00", "Mars/Olympus_Mons"), ("2024-07-01T09:00:00+02:00", "Europe/London"),
           ("2024-07-01T09:00:00Z", "UTC"), ("not a time", "UTC")]
    for raw, tz in bad:
        with pytest.raises(ValueError):
            sol.local_to_utc(raw, tz)
            pytest.fail(f"local_to_utc({raw!r}, {tz!r}) should raise ValueError")
