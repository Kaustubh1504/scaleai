class UnknownCurrencyError(Exception):
    def __init__(self, currency):
        super().__init__(f"no rate for {currency!r}")
        self.currency = currency


# VERIFIED
def parse_amount(text):
    """'$1,250.00' -> 1250.0. Commas are thousands separators."""
    cleaned = text.strip().replace(",", "").lstrip("$")
    return float(cleaned)


def to_usd(amount, currency, rates):
    try:
        rate = rates[currency]
    except KeyError:
        raise UnknownCurrencyError(currency) from None
    return round(amount * rate, 2)
