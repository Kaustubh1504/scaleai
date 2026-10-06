import csv
import json

from .cache import TTLCache
from .origin import norm_locale, parse_time


def load_trace(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append({
                "request_id": row["request_id"].strip().upper(),
                "ts": parse_time(row["ts"]),
                "client": row["client"].strip().lower(),
                "project": row["project"].strip().lower(),
                "locale": norm_locale(row["locale"]),
            })
    return sorted(rows, key=lambda r: r["ts"])


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class GuidelineService:
    def __init__(self, origin, config):
        self.origin = origin
        self.ttl_s = config["ttl_s"]
        self.default_ttl_s = config["default_ttl_s"]
        self.overrides = config.get("overrides", {})
        self.cache = TTLCache()

    def lookup(self, req):
        key = req["project"]
        value = self.cache.get(key, req["ts"])
        outcome = "hit"
        if value is None:
            value = self.origin.fetch(req["project"], req["locale"], req["ts"])
            if value is None:
                return "not_found", None
            self.cache.put(key, value, req["ts"], self.ttl_s.get(req["project"], self.default_ttl_s))
            outcome = "miss"
        extra = self.overrides.get(req["client"], {}).get(req["project"], [])
        value["labels"].extend(extra)
        return outcome, value
