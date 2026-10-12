"""16. Cache responses: reference solution."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, Hashable

import httpx

_MISSING = object()


class ApiError(Exception):
    def __init__(self, status: int, path: str, message: str = ""):
        super().__init__(f"{status} on {path}: {message}")
        self.status = status
        self.path = path


def enrich_orders(client: httpx.Client, orders: list[dict]) -> list[dict]:
    users: dict[str, dict | None] = {}
    out = []
    for order in orders:
        uid = order["user_id"]
        if uid not in users:
            resp = client.get(f"/v1/users/{uid}")
            if resp.status_code != 404 and not resp.is_success:
                raise ApiError(resp.status_code, f"/v1/users/{uid}", resp.text)
            users[uid] = None if resp.status_code == 404 else resp.json()
        out.append({**order, "user": users[uid]})
    return out


class TTLCache:
    def __init__(self, clock: Any, ttl_s: float, max_items: int | None = None):
        self.clock = clock
        self.ttl_s = ttl_s
        self.max_items = max_items
        self.data: OrderedDict = OrderedDict()  # key -> (expires_at, value)

    def get(self, key: Hashable, default: Any = None) -> Any:
        expires_at, value = self.data.get(key, (0.0, default))
        if self.clock.time() >= expires_at:
            self.data.pop(key, None)
            return default
        self.data.move_to_end(key)
        return value

    def set(self, key: Hashable, value: Any) -> None:
        self.data[key] = (self.clock.time() + self.ttl_s, value)
        self.data.move_to_end(key)
        if self.max_items is not None and len(self.data) > self.max_items:
            self.data.popitem(last=False)

    def get_or_load(self, key: Hashable, loader: Callable[[], Any]) -> Any:
        value = self.get(key, _MISSING)
        if value is _MISSING:
            value = loader()
            self.set(key, value)
        return value


if __name__ == "__main__":
    from kit import FakeClock
    from problem_api import make_api, make_orders

    api = make_api()
    enriched = enrich_orders(api.client(), make_orders())
    print(len(enriched), "orders,", len(api.log), "user lookups")
    print(enriched[0])

    clock = FakeClock()
    cache = TTLCache(clock, ttl_s=60, max_items=2)
    print(cache.get_or_load("a", lambda: "loaded a"), cache.get("a"))
    clock.advance(60)
    print("after 60 s:", cache.get("a", "expired"))
