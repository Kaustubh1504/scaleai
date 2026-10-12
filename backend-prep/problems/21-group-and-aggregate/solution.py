"""21. Group and aggregate orders: reference solution."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone


def _month(ts: str) -> str:
    return datetime.fromisoformat(ts).astimezone(timezone.utc).strftime("%Y-%m")


def _half_up(a: int, b: int) -> int:
    return (2 * a + b) // (2 * b)  # exact a / b rounded half up; round() rounds half to even


def revenue_by_customer_month(orders: list[dict]) -> dict[str, dict[str, int]]:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for o in orders:
        totals[o["customer_id"]][_month(o["created_at"])] += o["total_cents"]
    return {cust: dict(sorted(months.items())) for cust, months in sorted(totals.items())}


def top_customers_per_region(orders: list[dict], k: int = 3) -> dict[str, list[tuple[str, int]]]:
    if k < 1:
        raise ValueError("k must be at least 1")
    per_region: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for o in orders:
        per_region[o["region"]][o["customer_id"]] += o["total_cents"]
    return {region: sorted(custs.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
            for region, custs in sorted(per_region.items())}


def monthly_summary(orders: list[dict]) -> list[dict]:
    by_month: dict[str, list[int]] = defaultdict(list)
    for o in orders:
        by_month[_month(o["created_at"])].append(o["total_cents"])
    rows = []
    for month, vals in sorted(by_month.items()):
        s = sorted(vals)
        mid = len(s) // 2
        median = s[mid] if len(s) % 2 else _half_up(s[mid - 1] + s[mid], 2)
        rows.append({"month": month, "count": len(s), "total_cents": sum(s),
                     "average_cents": _half_up(sum(s), len(s)), "median_cents": median})
    return rows


if __name__ == "__main__":
    from problem_api import ORDERS

    print(revenue_by_customer_month(ORDERS))
    print(top_customers_per_region(ORDERS, k=3))
    for row in monthly_summary(ORDERS):
        print(row)
