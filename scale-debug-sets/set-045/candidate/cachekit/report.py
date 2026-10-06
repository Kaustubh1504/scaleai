import csv

from .client import QuoteService
from .origin import DATA_DIR, PriceOrigin, clean, load_config, parse_time


def load_requests(path, default_region):
    with open(path or DATA_DIR / "requests.csv", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            yield {
                "id": clean(row["request_id"]).upper(),
                "at": parse_time(row["at"]),
                "tenant": clean(row["tenant"]).lower(),
                "model": clean(row["model"]).lower(),
                "region": clean(row["region"]).lower() or default_region,
            }


def build_report(requests_path=None, prices_path=None, config_path=None):
    config = load_config(config_path)
    origin = PriceOrigin(prices_path)
    service = QuoteService(origin, config)
    served, tenants, stale = {}, {}, []
    for req in load_requests(requests_path, config["default_region"]):
        result = service.quote(req["tenant"], req["model"], req["region"], req["at"])
        served[req["id"]] = {"hit": result["hit"], "price": result["price"]}
        t = tenants.setdefault(req["tenant"], {"requests": 0, "hits": 0, "spend": 0.0})
        t["requests"] += 1
        t["hits"] += result["hit"]
        t["spend"] = round(t["spend"] + result["price"], 4)
        if result["base"] != origin.price_at(req["model"], req["region"], req["at"]):
            stale.append(req["id"])
    return {
        "requests": served,
        "tenants": dict(sorted(tenants.items())),
        "origin_calls": origin.calls,
        "stale_served": stale,
    }
