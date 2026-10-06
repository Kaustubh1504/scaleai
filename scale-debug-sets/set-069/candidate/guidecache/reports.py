from collections import Counter
from pathlib import Path

from .origin import GuidelineOrigin
from .service import GuidelineService, load_config, load_trace

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    origin = GuidelineOrigin(data_dir / "guidelines.json")
    service = GuidelineService(origin, load_config(data_dir / "config.json"))
    lookups, payloads = {}, {}
    for req in load_trace(data_dir / "trace.csv"):
        outcome, value = service.lookup(req)
        lookups[req["request_id"]] = {
            "project": req["project"],
            "outcome": outcome,
            "version": value["version"] if value else None,
            "locale": value["locale"] if value else None,
        }
        payloads[req["request_id"]] = value["labels"] if value else None
    return {
        "lookups": lookups,
        "payloads": payloads,
        "origin_fetches": dict(sorted(Counter(p for p, _ in origin.fetches).items())),
    }
