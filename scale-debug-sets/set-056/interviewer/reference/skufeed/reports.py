from collections import Counter, defaultdict
from pathlib import Path

from .dedupe import latest_by_sku, live_catalog
from .readers import feed_paths, load_categories, read_feed
from .validate import validate_feed

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def ingest(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    registry = load_categories(data_dir / "categories.json")
    accepted, rejected, per_source = [], [], {}
    for path in feed_paths(data_dir / "feeds"):
        ok, bad = validate_feed(path.stem, read_feed(path), registry)
        accepted.extend(ok)
        rejected.extend(bad)
        per_source[path.stem] = len(ok)
    return accepted, rejected, per_source


def summarize(accepted, winners, catalog, rejected):
    groups = defaultdict(list)
    for rec in catalog:
        groups[rec.category].append(rec)
    categories = {}
    for code in sorted(groups):
        items = groups[code]
        prices = [r.price_cents for r in items]
        categories[code] = {
            "skus": len(items),
            "units": sum(r.qty for r in items),
            "avg_price": round(sum(prices) / len(prices) / 100, 2),
            "stock_value": round(sum(r.price_cents * r.qty for r in items) / 100, 2),
        }
    top = min(categories, key=lambda c: (-categories[c]["stock_value"], c)) if categories else None
    return {
        "categories": categories,
        "top_category": top,
        "discontinued": sum(1 for r in winners.values() if r.discontinued),
        "duplicates_removed": len(accepted) - len(winners),
        "rejected": dict(sorted(Counter(r.reason for r in rejected).items())),
    }


def build_report(data_dir=DATA_DIR):
    accepted, rejected, per_source = ingest(data_dir)
    winners = latest_by_sku(accepted)
    catalog = live_catalog(winners)
    return {
        "accepted": per_source,
        "rejects": [(r.source, r.line, r.reason) for r in rejected],
        "catalog": {
            r.sku: {"title": r.title, "category": r.category, "price_cents": r.price_cents,
                    "qty": r.qty, "source": r.source}
            for r in catalog
        },
        "summary": summarize(accepted, winners, catalog, rejected),
    }
