"""16. Cache responses: dedupe lookups and a TTL cache

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
from collections import OrderedDict
from typing import Any, Callable, Hashable
import httpx


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def fetch_user(client: httpx.Client, user_id: str) -> dict | None:
    raise NotImplementedError


def enrich_orders(client: httpx.Client, orders: list[dict]) -> list[dict]:
    raise NotImplementedError


class TTLCache:
    def __init__(self, clock: Any, ttl_s: float, max_items: int | None = None):
        self.clock = clock
        self.ttl_s = ttl_s
        self.max_items = max_items
        self._data: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()  # key -> (expires_at, value)

    def get(self, key: Hashable, default: Any = None) -> Any:
        raise NotImplementedError

    def set(self, key: Hashable, value: Any) -> None:
        raise NotImplementedError

    def get_or_load(self, key: Hashable, loader: Callable[[], Any]) -> Any:
        raise NotImplementedError


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api, make_orders

    api = make_api()
    orders = make_orders()
    enriched = enrich_orders(api.client(), orders)
    print(len(enriched), "orders,", len(api.log), "user lookups,",
          sum(o["user"] is None for o in enriched), "orders with a deleted user")
    print(enriched[0])

    clock = FakeClock()
    cache = TTLCache(clock, ttl_s=60, max_items=2)
    print(cache.get_or_load("a", lambda: "loaded a"), cache.get("a"))
    clock.advance(60)
    print("after 60 s:", cache.get("a", "expired"))
