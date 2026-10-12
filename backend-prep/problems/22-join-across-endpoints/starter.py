"""22. Joining three paginated endpoints

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import Counter
from typing import Iterator
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def iter_orders(client: httpx.Client) -> Iterator[dict]:
    raise NotImplementedError


def iter_customers(client: httpx.Client) -> Iterator[dict]:
    raise NotImplementedError


def iter_products(client: httpx.Client) -> Iterator[dict]:
    raise NotImplementedError


def build_report(client: httpx.Client) -> dict:
    # One crawl per collection, then join in memory with dict lookups.
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import make_api

    api = make_api()
    report = build_report(api.client())
    for row in report["customers"][:5]:
        print(row)
    print("...", len(report["customers"]), "customers")
    for o in report["orphans"]:
        print("orphan:", o)
    print(len(api.log), "requests:", sorted({c.path for c in api.log}))
