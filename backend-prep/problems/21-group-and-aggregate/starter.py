"""21. Group and aggregate orders

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone


def utc_month(ts: str) -> str:
    """'2024-01-31T22:30:00-05:00' -> '2024-02' (the month in UTC)."""
    raise NotImplementedError


def div_half_up(a: int, b: int) -> int:
    """a / b rounded half-up, exact integer arithmetic (a >= 0, b > 0). round() would round half to even."""
    raise NotImplementedError


def median_half_up(values: list[int]) -> int:
    raise NotImplementedError


def revenue_by_customer_month(orders: list[dict]) -> dict[str, dict[str, int]]:
    raise NotImplementedError


def top_customers_per_region(orders: list[dict], k: int = 3) -> dict[str, list[tuple[str, int]]]:
    raise NotImplementedError


def monthly_summary(orders: list[dict]) -> list[dict]:
    raise NotImplementedError


if __name__ == "__main__":
    from pprint import pprint

    from problem_api import ORDERS

    pprint(revenue_by_customer_month(ORDERS), sort_dicts=False)
    pprint(top_customers_per_region(ORDERS, k=3), sort_dicts=False)
    for row in monthly_summary(ORDERS):
        print(row)
