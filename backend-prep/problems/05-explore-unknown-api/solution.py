"""05. Explore an unknown API via OpenAPI: reference solution."""

from __future__ import annotations

from collections import Counter

import httpx


def customer_with_most_open_tickets(client: httpx.Client, api_key: str) -> dict | None:
    # Per /openapi.json: X-Support-Key header; /v1/tickets is cursor-paged with limit <= 50.
    headers = {"X-Support-Key": api_key}
    params = {"status": "open", "limit": 50}
    counts = Counter()
    while True:
        resp = client.get("/v1/tickets", params=params, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        counts.update(t["customer_id"] for t in body["results"])
        if body.get("next_cursor") is None:
            break
        params["cursor"] = body["next_cursor"]
    if not counts:
        return None
    customer_id, n_open = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    resp = client.get(f"/v1/customers/{customer_id}", headers=headers)
    resp.raise_for_status()
    return {"customer_id": customer_id, "name": resp.json()["name"], "open_tickets": n_open}


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    for kwargs in ({}, {"top_ids": (4, 9)}, {"no_open": True}):
        print(kwargs, customer_with_most_open_tickets(make_api(**kwargs).client(), API_KEY))
