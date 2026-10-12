"""05. Explore an unknown API via OpenAPI

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import Counter
from typing import Iterator
import httpx

AUTH_HEADER = "X-Support-Key"
TICKET_PAGE_SIZE = 50 


def iter_open_tickets(client: httpx.Client, headers: dict[str, str]) -> Iterator[dict]:
    params ={'status':'open'}
    
    while True:
        res = client.get("/v1/tickets",headers=headers, params=params)
        res.raise_for_status()
        body = res.json()
        for item in body["results"]:
            yield item
        cursor = body.get("next_cursor")
        if not cursor:
            break
        params['cursor']=cursor
        

def customer_with_most_open_tickets(client: httpx.Client, api_key: str) -> dict | None:
    headers = {AUTH_HEADER:api_key}
    tickets = iter_open_tickets(client=client,headers=headers)
    
    counts = Counter(t["customer_id"] for t in tickets)
    if not counts:
        return None
    
    customer_id, open_tickets = min(counts.items(), key=lambda k: (-k[1],k[0]))
    res = client.get(f"/v1/customers/{customer_id}", headers=headers)
    res.raise_for_status()
    return {"customer_id": customer_id, "name": res.json()["name"], "open_tickets": open_tickets}
        


if __name__ == "__main__":
    from problem_api import API_KEY, make_api
    

    for kwargs in ({}, {"top_ids": (4, 9)}, {"no_open": True}):
        api = make_api(**kwargs)
        print(kwargs, customer_with_most_open_tickets(api.client(), API_KEY), f"({len(api.log)} requests)")
