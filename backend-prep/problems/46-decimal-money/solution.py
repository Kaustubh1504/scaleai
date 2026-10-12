"""46. Money with Decimal: reference solution."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Iterable


def parse_dollars(s: str) -> int:
    cleaned = s.strip().removeprefix("$").replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?|\.\d{1,2}", cleaned):
        raise ValueError(f"not a dollar amount: {s!r}")
    return int(Decimal(cleaned) * 100)


def split_cents(total_cents: int, n: int) -> list[int]:
    if n < 1:
        raise ValueError("n must be >= 1")
    base, leftover = divmod(total_cents, n)
    return [base + 1 if i < leftover else base for i in range(n)]


def tax_cents(amount_cents: int, rate_percent: str | Decimal, rounding: str = ROUND_HALF_UP) -> int:
    if not isinstance(rate_percent, (str, Decimal)):
        raise TypeError("rate_percent must be str or Decimal")
    return int((amount_cents * Decimal(rate_percent) / 100).quantize(Decimal(1), rounding=rounding))


def total_dollars(amounts: Iterable[str]) -> Decimal:
    return sum(map(Decimal, amounts), Decimal(0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


if __name__ == "__main__":
    print(parse_dollars("$1,234.5"), split_cents(1000, 3))
    print(tax_cents(50, "5"), tax_cents(50, "5", rounding=ROUND_HALF_EVEN))
    print(total_dollars(["0.10", "0.20"]), total_dollars(["1.005"]))
