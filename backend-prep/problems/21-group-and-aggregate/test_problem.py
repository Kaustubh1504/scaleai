import copy

import pytest

from problem_api import ORDERS


def order(cid, created_at, cents, region="us-east", oid="o"):
    return {"order_id": oid, "customer_id": cid, "region": region, "created_at": created_at, "total_cents": cents}


def test_revenue_by_customer_month(sol):
    """revenue_by_customer_month sums cents per customer per UTC month"""
    assert sol.revenue_by_customer_month(ORDERS) == {
        "cus_acme": {"2024-01": 15000, "2024-02": 5000},
        "cus_bolt": {"2024-02": 15002},
        "cus_cora": {"2024-01": 9999, "2024-02": 20000},
        "cus_dune": {"2024-03": 22002},
        "cus_echo": {"2023-12": 4500, "2024-03": 7000},
    }


def test_revenue_keys_sorted(sol):
    """Customer keys and month keys come out sorted (insertion order)"""
    out = sol.revenue_by_customer_month(ORDERS)
    assert list(out) == sorted(out), "customer ids must be in sorted order"
    for cid, months in out.items():
        assert list(months) == sorted(months), f"months for {cid} must be sorted, got {list(months)}"


def test_months_are_utc(sol):
    """Offsets are converted to UTC before taking the month (both directions)"""
    orders = [order("c1", "2024-01-31T22:30:00-05:00", 100),   # Feb 1 03:30 UTC
              order("c1", "2024-03-01T00:30:00+02:00", 200),   # Feb 29 22:30 UTC
              order("c1", "2024-04-30T23:59:59Z", 300),
              order("c1", "2024-05-01T00:00:00+00:00", 400)]
    assert sol.revenue_by_customer_month(orders) == {"c1": {"2024-02": 300, "2024-04": 300, "2024-05": 400}}


def test_top_customers_with_ties(sol):
    """Top k per region: cents descending, ties by customer id ascending, regions sorted"""
    out = sol.top_customers_per_region(ORDERS, k=3)
    assert list(out) == ["apac", "eu-west", "us-east"], "region keys must be sorted"
    assert out["us-east"] == [("cus_bolt", 15002), ("cus_dune", 15002), ("cus_acme", 15000)]
    assert out["apac"] == [("cus_dune", 7000), ("cus_echo", 7000)], "tie on 7000: cus_dune before cus_echo"
    assert out["eu-west"] == [("cus_cora", 29999), ("cus_acme", 5000)]


def test_top_customers_per_region_is_regional(sol):
    """A customer's spend is counted per region, not across regions"""
    orders = [order("big", "2024-01-01T00:00:00Z", 50, "apac"), order("big", "2024-01-01T00:00:00Z", 50, "us-east"),
              order("mid", "2024-01-01T00:00:00Z", 60, "us-east")]
    assert sol.top_customers_per_region(orders, k=1) == {"apac": [("big", 50)], "us-east": [("mid", 60)]}


def test_top_customers_k(sol):
    """k=1 keeps only the leader; k larger than the region returns everyone; k=0 raises ValueError"""
    assert sol.top_customers_per_region(ORDERS, k=1)["us-east"] == [("cus_bolt", 15002)]
    assert len(sol.top_customers_per_region(ORDERS, k=10)["us-east"]) == 4
    with pytest.raises(ValueError):
        sol.top_customers_per_region(ORDERS, k=0)


def test_monthly_summary(sol):
    """monthly_summary gives count, total, half-up average and median per month, sorted"""
    assert sol.monthly_summary(ORDERS) == [
        {"month": "2023-12", "count": 1, "total_cents": 4500, "average_cents": 4500, "median_cents": 4500},
        {"month": "2024-01", "count": 3, "total_cents": 24999, "average_cents": 8333, "median_cents": 9999},
        {"month": "2024-02", "count": 4, "total_cents": 40002, "average_cents": 10001, "median_cents": 10000},
        {"month": "2024-03", "count": 3, "total_cents": 29002, "average_cents": 9667, "median_cents": 7000},
    ]


def test_average_rounds_half_up(sol):
    """average_cents rounds .5 up (2.5 -> 3, 4.5 -> 5), unlike round()"""
    rows = sol.monthly_summary([order("c", "2024-01-01T00:00:00Z", 1), order("c", "2024-01-02T00:00:00Z", 4),
                                order("c", "2024-02-01T00:00:00Z", 4), order("c", "2024-02-02T00:00:00Z", 5)])
    assert [r["average_cents"] for r in rows] == [3, 5], "2.5 -> 3 and 4.5 -> 5 (round() gives 2 and 4)"
    assert all(isinstance(r["average_cents"], int) for r in rows), "averages must be ints"


def test_median_even_count(sol):
    """median_cents for an even count is the half-up mean of the two middle values"""
    rows = sol.monthly_summary([order("c", "2024-01-01T00:00:00Z", v) for v in (101, 900, 100, 0)])
    assert rows[0]["median_cents"] == 101, "middle values 100 and 101 -> 100.5 -> 101"
    assert isinstance(rows[0]["median_cents"], int)
    rows = sol.monthly_summary([order("c", "2024-01-01T00:00:00Z", v) for v in (7, 3, 5)])
    assert rows[0]["median_cents"] == 5


def test_empty_and_no_mutation(sol):
    """Empty input gives {}, {}, []; the input list is never modified"""
    assert sol.revenue_by_customer_month([]) == {}
    assert sol.top_customers_per_region([]) == {}
    assert sol.monthly_summary([]) == []
    before = copy.deepcopy(ORDERS)
    sol.revenue_by_customer_month(ORDERS)
    sol.top_customers_per_region(ORDERS)
    sol.monthly_summary(ORDERS)
    assert ORDERS == before, "don't sort or modify the caller's list"
