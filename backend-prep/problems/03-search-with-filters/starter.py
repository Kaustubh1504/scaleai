"""03. Search orders with query filters

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from datetime import datetime, timezone
import httpx

SORTS = ("created_at", "-created_at", "total_cents", "-total_cents")


def search_orders(client: httpx.Client, *, status: list[str] | None = None,
                  since: datetime | None = None, until: datetime | None = None,
                  min_total_cents: int | None = None, include_archived: bool | None = None,
                  sort: str | None = None) -> list[dict]:
    # Validate and build everything first, so a bad argument never costs a request.
    raise NotImplementedError


if __name__ == "__main__":
    from datetime import timedelta

    from problem_api import make_api

    api = make_api()
    ist = timezone(timedelta(hours=5, minutes=30))
    orders = search_orders(api.client(), status=["paid", "shipped"], since=datetime(2024, 3, 4, tzinfo=ist),
                           include_archived=False, sort="-total_cents")
    print(api.log[-1].multi_params)
    for o in orders:
        print(" ", o["id"], o["status"], o["total_cents"], o["created_at"])
