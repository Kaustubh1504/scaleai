from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

import pytest


def test_parse_basic(sol):
    """parse_dollars converts plain amounts to exact integer cents"""
    assert sol.parse_dollars("12.34") == 1234
    assert sol.parse_dollars("0.07") == 7
    assert sol.parse_dollars("19.99") == 1999, "float('19.99') * 100 == 1998.9999999999998"
    assert sol.parse_dollars("7") == 700
    assert isinstance(sol.parse_dollars("1.10"), int)


def test_parse_decorations(sol):
    """parse_dollars accepts whitespace, a leading $, thousands commas and '.5'"""
    assert sol.parse_dollars("  $1,234.50 ") == 123450
    assert sol.parse_dollars("$1,234.5") == 123450
    assert sol.parse_dollars(".5") == 50


def test_parse_rejects_junk(sol):
    """parse_dollars raises ValueError for junk, negatives, exponents, NaN and >2 decimals"""
    accepted = []
    for bad in ["", "   ", "abc", "1.234", "-3.10", "1e3", "NaN", "inf", "$", "12.3.4", "1 2"]:
        try:
            result = sol.parse_dollars(bad)
        except ValueError:
            continue
        accepted.append((bad, result))
    assert not accepted, f"these should raise ValueError but returned a value: {accepted}"


def test_split_leftover_to_first(sol):
    """split_cents sums to the total and gives the leftover cents to the first parts"""
    assert sol.split_cents(1000, 3) == [334, 333, 333]
    assert sol.split_cents(1001, 4) == [251, 250, 250, 250]
    assert sol.split_cents(2, 5) == [1, 1, 0, 0, 0]
    assert sol.split_cents(900, 3) == [300, 300, 300]
    assert sum(sol.split_cents(123457, 7)) == 123457


def test_split_bad_n(sol):
    """split_cents with n < 1 raises ValueError"""
    with pytest.raises(ValueError):
        sol.split_cents(100, 0)


def test_tax_half_up_vs_half_even(sol):
    """tax_cents rounds half up by default and to even with ROUND_HALF_EVEN"""
    assert sol.tax_cents(50, "5") == 3, "2.5 cents rounds half up to 3"
    assert sol.tax_cents(50, "5", rounding=ROUND_HALF_EVEN) == 2, "2.5 cents rounds half even to 2"
    assert sol.tax_cents(70, "5", rounding=ROUND_HALF_EVEN) == 4, "3.5 cents rounds half even to 4"
    assert sol.tax_cents(70, "5", rounding=ROUND_HALF_UP) == 4


def test_tax_exact_rates(sol):
    """tax_cents is exact for rates like 8.875% and accepts Decimal"""
    assert sol.tax_cents(10000, "8.875") == 888, "887.5 cents -> 888"
    assert sol.tax_cents(10000, Decimal("8.875"), rounding=ROUND_HALF_EVEN) == 888, "887.5 -> 888 (8 is even)"
    assert sol.tax_cents(1999, "7.25") == 145, "144.9275 -> 145"


def test_tax_rejects_float(sol):
    """tax_cents raises TypeError when given a float rate"""
    with pytest.raises(TypeError):
        sol.tax_cents(1000, 8.875)


def test_total_exact(sol):
    """total_dollars sums exactly and returns a Decimal quantized to cents"""
    got = sol.total_dollars(["0.10", "0.20"])
    assert isinstance(got, Decimal)
    assert got == Decimal("0.30") and str(got) == "0.30"
    assert sol.total_dollars(["0.1"] * 10) == Decimal("1.00")
    assert str(sol.total_dollars([])) == "0.00"


def test_total_rounds_half_up_exactly(sol):
    """total_dollars(['1.005']) is 1.01: summing floats would give 1.00"""
    assert sol.total_dollars(["1.005"]) == Decimal("1.01"), "float 1.005 is 1.00499999..., so it rounds down"
    assert sol.total_dollars(["0.335", "0.335", "0.335"]) == Decimal("1.01"), "1.005 exactly rounds half up"
