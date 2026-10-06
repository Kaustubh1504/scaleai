from dataclasses import dataclass

from .cache import TTLCache
from .origin import Origin, UnknownPrice


@dataclass
class Response:
    req_id: str
    outcome: str
    price: float | None


def request_key(req):
    return (req.endpoint, req.sku, req.region)


def serve(req, cache, origin, discounts):
    key = request_key(req)
    quote = cache.get(key, req.ts)
    outcome = "hit"
    if quote is None:
        outcome = "miss"
        try:
            quote = origin.fetch(req.endpoint, req.sku, req.region, req.currency)
        except UnknownPrice:
            return Response(req.req_id, "error", None)
        cache.put(key, quote, req.ts)
    if req.endpoint == "quote":
        pct = discounts.get(req.client, 0.0)
        quote["price"] = round(quote["price"] * (1 - pct / 100), 2)
    return Response(req.req_id, outcome, quote["price"])


def replay(requests, invalidations, ttls, prices, discounts):
    cache = TTLCache(ttls)
    origin = Origin(prices)
    # invalidations sort before requests that share their timestamp
    events = [(inv.ts, 0, n, inv) for n, inv in enumerate(invalidations)]
    events += [(req.ts, 1, n, req) for n, req in enumerate(requests)]
    responses = []
    for _, kind, _, event in sorted(events, key=lambda e: e[:3]):
        if kind == 0:
            cache.invalidate_sku(event.sku)
        else:
            responses.append(serve(event, cache, origin, discounts))
    return responses, origin
