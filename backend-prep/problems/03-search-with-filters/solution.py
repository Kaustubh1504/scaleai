"""03. Search orders with query filters: reference solution."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

SORTS = ("created_at", "-created_at", "total_cents", "-total_cents")


def search_orders(client: httpx.Client, *, status: list[str] | None = None,
                  since: datetime | None = None, until: datetime | None = None,
                  min_total_cents: int | None = None, include_archived: bool | None = None,
                  sort: str | None = None) -> list[dict]:
    params = [("status", s) for s in status or []]
    for name, dt in (("since", since), ("until", until)):
        if dt is not None:
            if dt.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
            params.append((name, dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    if min_total_cents is not None:
        if min_total_cents < 0:
            raise ValueError("min_total_cents must be >= 0")
        params.append(("min_total_cents", str(min_total_cents)))
    if include_archived is not None:
        params.append(("include_archived", "true" if include_archived else "false"))
    if sort is not None:
        if sort not in SORTS:
            raise ValueError(f"sort must be one of {SORTS}")
        params.append(("sort", sort))
    resp = client.get("/v1/orders", params=params)
    resp.raise_for_status()
    return resp.json()["data"]


if __name__ == "__main__":
    from datetime import timedelta

    from problem_api import make_api

    api = make_api()
    ist = timezone(timedelta(hours=5, minutes=30))
    orders = search_orders(api.client(), status=["paid", "shipped"], sort="-total_cents",
                           since=datetime(2024, 3, 4, tzinfo=ist), include_archived=False)
    print(api.log[-1].multi_params)
    for o in orders:
        print(" ", o["id"], o["status"], o["total_cents"], o["created_at"])
