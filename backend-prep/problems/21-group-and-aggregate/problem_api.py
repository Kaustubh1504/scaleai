"""Sample labeling-service orders for problem 21 (in no particular order)."""

from __future__ import annotations

ORDERS: list[dict] = [
    {"order_id": "ord_09", "customer_id": "cus_dune", "region": "us-east", "created_at": "2024-03-09T12:00:00Z", "total_cents": 15002},
    {"order_id": "ord_01", "customer_id": "cus_acme", "region": "us-east", "created_at": "2024-01-05T10:00:00Z", "total_cents": 12000},
    {"order_id": "ord_10", "customer_id": "cus_echo", "region": "apac", "created_at": "2024-03-15T12:00:00Z", "total_cents": 7000},
    {"order_id": "ord_04", "customer_id": "cus_bolt", "region": "us-east", "created_at": "2024-01-31T22:30:00-05:00", "total_cents": 15000},
    {"order_id": "ord_06", "customer_id": "cus_cora", "region": "eu-west", "created_at": "2024-01-15T08:00:00Z", "total_cents": 9999},
    {"order_id": "ord_02", "customer_id": "cus_acme", "region": "us-east", "created_at": "2024-01-20T09:00:00Z", "total_cents": 3000},
    {"order_id": "ord_11", "customer_id": "cus_echo", "region": "us-east", "created_at": "2023-12-31T23:59:59Z", "total_cents": 4500},
    {"order_id": "ord_03", "customer_id": "cus_acme", "region": "eu-west", "created_at": "2024-02-02T11:00:00+01:00", "total_cents": 5000},
    {"order_id": "ord_07", "customer_id": "cus_cora", "region": "eu-west", "created_at": "2024-03-01T00:30:00+02:00", "total_cents": 20000},
    {"order_id": "ord_05", "customer_id": "cus_bolt", "region": "us-east", "created_at": "2024-02-10T00:00:00Z", "total_cents": 2},
    {"order_id": "ord_08", "customer_id": "cus_dune", "region": "apac", "created_at": "2024-03-03T05:00:00+08:00", "total_cents": 7000},
]
