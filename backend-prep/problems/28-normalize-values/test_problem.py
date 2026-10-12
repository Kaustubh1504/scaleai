from decimal import Decimal

import pytest

from problem_api import LABEL_MAPPING

MISSING = [None, float("nan"), "", "   ", "N/A", "n/a", "NA", "NULL", "null", "None", "-", " - ", "nan", "NaN"]


def test_missing_markers(sol):
    """parse_missing maps None, NaN, blanks and N/A-style markers to None"""
    for v in MISSING:
        assert sol.parse_missing(v) is None, f"parse_missing({v!r}) should be None"


def test_real_values_pass_through(sol):
    """parse_missing strips real strings and leaves 0, 0.0 and False alone"""
    assert sol.parse_missing("  cat ") == "cat", "real strings come back stripped"
    assert sol.parse_missing("0") == "0"
    for v in (0, 0.0, False, Decimal("0")):
        out = sol.parse_missing(v)
        assert out == v and type(out) is type(v), f"{v!r} is a real value, not missing"


def test_parse_number_formats(sol):
    """parse_number handles plain, $, thousands, accounting (x), %, and scientific inputs"""
    cases = {
        "42": Decimal("42"), " 3.50 ": Decimal("3.50"), ".5": Decimal("0.5"),
        "1,234.50": Decimal("1234.50"), "$1,234,567": Decimal("1234567"),
        "-$5": Decimal("-5"), "+7": Decimal("7"),
        "(5.00)": Decimal("-5.00"), "($1,000)": Decimal("-1000"),
        "12%": Decimal("0.12"), "-2.5%": Decimal("-0.025"),
        "1e3": Decimal("1000"), "2.5E-2": Decimal("0.025"),
    }
    for raw, want in cases.items():
        got = sol.parse_number(raw)
        assert isinstance(got, Decimal), f"parse_number({raw!r}) must return a Decimal, got {type(got).__name__}"
        assert got == want, f"parse_number({raw!r}) = {got!r}, expected {want!r}"


def test_parse_number_exact_decimal(sol):
    """parse_number keeps digits exactly: "1,234.50" -> Decimal("1234.50") and 0.1 -> Decimal("0.1")"""
    assert str(sol.parse_number("1,234.50")) == "1234.50", "keep the digits as written (no float in between)"
    assert sol.parse_number(0.1) == Decimal("0.1"), "convert floats via str(), not Decimal(0.1)"
    assert sol.parse_number(7) == Decimal(7)
    assert sol.parse_number(Decimal("2.5")) == Decimal("2.5")
    assert sol.parse_number(" n/a ") is None, "missing input returns None"


def test_parse_number_rejects_garbage(sol):
    """parse_number raises ValueError for True, inf, bad grouping and junk"""
    for raw in (True, "inf", "Infinity", "12,34", "1.2.3", "$", "--5", "(-5)", "$5%", "12abc", "abc", float("inf")):
        with pytest.raises(ValueError):
            sol.parse_number(raw)
            pytest.fail(f"parse_number({raw!r}) should raise ValueError")


def test_parse_bool_spellings(sol):
    """parse_bool accepts yes/no, y/n, true/false, t/f, 1/0, on/off in any case and spacing"""
    for raw in ("true", "TRUE", " Yes ", "y", "T", "1", "on", " ON ", 1, True):
        assert sol.parse_bool(raw) is True, f"parse_bool({raw!r}) should be True"
    for raw in ("false", "False", "no", " N ", "f", "0", "off", "OFF", 0, False):
        assert sol.parse_bool(raw) is False, f"parse_bool({raw!r}) should be False (never bool(str))"
    assert sol.parse_bool("null") is None, "missing input returns None"


def test_parse_bool_rejects(sol):
    """parse_bool raises ValueError for "maybe", 2, 1.0 and other junk"""
    for raw in ("maybe", "yess", "2", 2, -1, 1.0, "true false"):
        with pytest.raises(ValueError):
            sol.parse_bool(raw)
            pytest.fail(f"parse_bool({raw!r}) should raise ValueError")


def test_split_multi(sol):
    """split_multi splits on ; | , , strips, drops blanks and dedupes keeping first order"""
    assert sol.split_multi("a; b|c, ,a") == ["a", "b", "c"]
    assert sol.split_multi("night;Night;night") == ["night", "Night"], "dedupe is case-sensitive"
    assert sol.split_multi(["night; rain", "rain|fog"]) == ["night", "rain", "fog"], "lists are chunks to split too"
    assert sol.split_multi("N/A") == [] and sol.split_multi(None) == [], "missing input returns []"
    assert sol.split_multi(" ;|, ") == [], "only separators means no values"


def test_normalize_id_keeps_leading_zeros(sol):
    """normalize_id strips, upper-cases and keeps leading zeros; ints become strings"""
    assert sol.normalize_id(" 007 ") == "007", "leading zeros are part of the id"
    assert sol.normalize_id("ann-07") == "ANN-07"
    assert sol.normalize_id("t_12") == "T_12"
    assert sol.normalize_id(42) == "42"
    assert sol.normalize_id("NULL") is None


def test_normalize_id_rejects(sol):
    """normalize_id raises ValueError for floats like 7.0, bools, negatives and bad characters"""
    for raw in (7.0, 7.5, True, -3, "T 9", "7.0", "ann#1"):
        with pytest.raises(ValueError):
            sol.normalize_id(raw)
            pytest.fail(f"normalize_id({raw!r}) should raise ValueError")


def test_normalize_category_synonyms(sol):
    """normalize_category maps synonyms case/space/underscore-insensitively to the canonical key"""
    cases = {
        "car": "vehicle", " Car ": "vehicle", "MOTOR_VEHICLE": "vehicle", "auto   mobile": "vehicle",
        "motor-vehicle": "vehicle", "Vehicle": "vehicle", "bike   rider": "cyclist", "PED": "pedestrian",
    }
    for raw, want in cases.items():
        assert sol.normalize_category(raw, LABEL_MAPPING) == want, f"{raw!r} should map to {want!r}"
    assert sol.normalize_category("Bike Rider", {"Cyclist": ["bike_rider"]}) == "Cyclist", \
        "return the canonical key exactly as written in the mapping"


def test_normalize_category_unknown_and_broken_mapping(sol):
    """normalize_category: missing -> None, unknown -> ValueError, ambiguous mapping -> ValueError"""
    assert sol.normalize_category("  N/A ", LABEL_MAPPING) is None
    with pytest.raises(ValueError):
        sol.normalize_category("horse", LABEL_MAPPING)
    with pytest.raises(ValueError):
        sol.normalize_category(3, LABEL_MAPPING)
    broken = {"vehicle": ["car", "bike"], "cyclist": ["Bike"]}
    with pytest.raises(ValueError):
        sol.normalize_category("car", broken)
        pytest.fail("'bike' maps to two canonicals: the mapping must be rejected")
