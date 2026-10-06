from .store import TTLCache


class QuoteService:
    def __init__(self, origin, config):
        self.origin = origin
        self.cache = TTLCache()
        self.ttls = config["ttl_seconds"]
        self.default_ttl = config["default_ttl_seconds"]
        self.discounts = config["discounts"]

    def ttl_for(self, model):
        return self.ttls.get(model) or self.default_ttl

    def cache_key(self, model, region):
        return model

    def quote(self, tenant, model, region, now):
        key = self.cache_key(model, region)
        value = self.cache.get(key, now)
        hit = value is not None
        if not hit:
            value = self.origin.fetch(model, region, now)
            ttl = self.ttl_for(model)
            if ttl > 0:
                self.cache.put(key, value, now, ttl)
        base = value["price"]
        value["price"] = round(base * (1 - self.discounts.get(tenant, 0)), 4)
        return {"hit": hit, "base": base, "price": value["price"]}
