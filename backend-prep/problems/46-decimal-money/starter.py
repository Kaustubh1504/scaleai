"""46. Money with Decimal

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Iterable

CENT = Decimal("0.01")


def parse_dollars(s: str) -> int:
    raise NotImplementedError


def split_cents(total_cents: int, n: int) -> list[int]:
    raise NotImplementedError


def tax_cents(amount_cents: int, rate_percent: str | Decimal, rounding: str = ROUND_HALF_UP) -> int:
    raise NotImplementedError


def total_dollars(amounts: Iterable[str]) -> Decimal:
    raise NotImplementedError


if __name__ == "__main__":
    print(parse_dollars("$1,234.5"), split_cents(1000, 3))
    print(tax_cents(50, "5"), tax_cents(50, "5", rounding=ROUND_HALF_EVEN))
    print(total_dollars(["0.10", "0.20"]), total_dollars(["1.005"]))
