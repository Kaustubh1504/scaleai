from .models import Record, Reject, RowError
from .utils import clean, parse_price, parse_qty, parse_updated


def build_record(source, line, row, registry):
    sku = clean(row.get("sku", "")).upper()
    if not sku:
        raise RowError("missing_sku")
    code = clean(row.get("category", "")).lower()
    category = registry.get(code)
    if category is None or not category.active:
        raise RowError("unknown_category")
    price = parse_price(row.get("price", ""))
    if price is None:
        raise RowError("bad_price")
    qty = parse_qty(row.get("qty", ""))
    updated_at = parse_updated(row.get("updated_at", ""))
    status = clean(row.get("status", "")).lower() or "active"
    return Record(sku, clean(row.get("title", "")), code, price, qty, updated_at, status, source, line)


def validate_feed(source, rows, registry):
    accepted, rejected = [], []
    for line, row in rows:
        try:
            accepted.append(build_record(source, line, row, registry))
        except RowError as err:
            rejected.append(Reject(source, line, err.reason))
    return accepted, rejected
