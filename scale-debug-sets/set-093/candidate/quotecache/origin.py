class UnknownPrice(LookupError):
    pass


class Origin:
    """The slow pricing service. Every fetch is counted."""

    def __init__(self, prices):
        self.prices = prices
        self.calls = []

    def fetch(self, endpoint, sku, region, currency):
        self.calls.append(sku)
        try:
            price = self.prices[(sku, region, currency)]
        except KeyError:
            raise UnknownPrice(f"no {currency} price for {sku} in {region}") from None
        return {"endpoint": endpoint, "sku": sku, "region": region, "currency": currency, "price": price}
