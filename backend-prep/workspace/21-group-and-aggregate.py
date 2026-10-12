"""21. Group and aggregate orders

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone


def utc_month(ts: str) -> str:
    """'2024-01-31T22:30:00-05:00' -> '2024-02' (the month in UTC)."""
    dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
    return dt.astimezone(timezone.utc).strftime("%Y-%m")


def div_half_up(a: int, b: int) -> int:
    """a / b rounded half-up, exact integer arithmetic (a >= 0, b > 0). round() would round half to even."""
    return (2 * a + b) // (2 * b)


def median_half_up(values: list[int]) -> int:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else div_half_up(s[mid - 1] + s[mid], 2)


def revenue_by_customer_month(orders: list[dict]) -> dict[str, dict[str, int]]:
    totals = defaultdict(lambda: defaultdict(int))
    for o in orders:
        month = utc_month(o["created_at"])
        total_cents = o["total_cents"]
        cust_id = o["customer_id"]
        totals[cust_id][month]+=total_cents
    
    return {
        cust: dict(sorted(months.items()))
        for cust, months in sorted(totals.items())
    }


def top_customers_per_region(orders: list[dict], k: int = 3) -> dict[str, list[tuple[str, int]]]:
    if k < 1:
        raise ValueError("k should be larger than 1")
        
    totals = defaultdict(lambda: defaultdict(int))
    
    for o in orders:
        region = o["region"]
        total_cents = o["total_cents"]
        cust_id = o["customer_id"]
        totals[region][cust_id]+=total_cents
    
    res = {
        region: sorted(custs.items(), key=lambda kv: (-kv[1],kv[0]) ) [:k]
        for region, custs in sorted(totals.items())
    }
    
    return res
    


def monthly_summary(orders: list[dict]) -> list[dict]:
    by_month = defaultdict(list)
    for o in orders:
        by_month[utc_month(o["created_at"])].append(o["total_cents"])
        
    return [
        {
            "month": month,
            "count": len(vals),
            "total_cents": sum(vals),
            "average_cents": div_half_up(sum(vals), len(vals)),
            "median_cents": median_half_up(vals) 
        }
        for month, vals in sorted(by_month.items())
    ]


if __name__ == "__main__":
    from pprint import pprint

    from problem_api import ORDERS

    pprint(revenue_by_customer_month(ORDERS), sort_dicts=False)
    pprint(top_customers_per_region(ORDERS, k=3), sort_dicts=False)
    for row in monthly_summary(ORDERS):
        print(row)
