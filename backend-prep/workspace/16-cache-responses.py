"""16. Cache responses: dedupe lookups and a TTL cache

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

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


def fetch_user(client: httpx.Client, user_id: str) -> dict | None:
    path = f"/v1/users/{user_id}"
    
    res = client.get(path)
    if res.is_success:
        try:
            return res.json()
        except:
            raise ValueError("Not valid json")
    
    status = res.status_code
    
    if status == 404:
        return None
    
    raise ApiError(status, path, res.text[:200])


def enrich_orders(client: httpx.Client, orders: list[dict]) -> list[dict]:
    unique_users = dict()
    enriched_orders = []
    for o in orders:
        u_id = o.get("user_id")
        
        if u_id not in unique_users:
            user = fetch_user(client, u_id)
            unique_users[u_id] = user
        else:
            user = unique_users.get(u_id)
        
        enriched_orders.append({**o, "user": user})
        
    return enriched_orders
        


class TTLCache:
    def __init__(self, clock: Any, ttl_s: float, max_items: int | None = None):
        self.clock = clock
        self.ttl_s = ttl_s
        self.max_items = max_items
        self._data: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()  # key -> (expires_at, value)

    def get(self, key: Hashable, default: Any = None) -> Any:
        entry = self._data.get(key)
        if not entry:
            return default
        expires_at, value = entry
        if self.clock.time()>=expires_at:
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def set(self, key: Hashable, value: Any) -> None:
        self._data[key]=(self.clock.time()+self.ttl_s, value)
        self._data.move_to_end(key)
        
        if self.max_items is not None:
            while len(self._data) > self.max_items:
                self._data.popitem(last=False)
        

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
