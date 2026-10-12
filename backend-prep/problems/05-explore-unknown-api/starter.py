"""05. Explore an unknown API via OpenAPI

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import Counter
from typing import Iterator
import httpx

AUTH_HEADER = "X-Support-Key"
TICKET_PAGE_SIZE = 50  # the spec's maximum for /v1/tickets


def iter_open_tickets(client: httpx.Client, headers: dict[str, str]) -> Iterator[dict]:
    raise NotImplementedError


def customer_with_most_open_tickets(client: httpx.Client, api_key: str) -> dict | None:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import API_KEY, make_api

    for kwargs in ({}, {"top_ids": (4, 9)}, {"no_open": True}):
        api = make_api(**kwargs)
        print(kwargs, customer_with_most_open_tickets(api.client(), API_KEY), f"({len(api.log)} requests)")
