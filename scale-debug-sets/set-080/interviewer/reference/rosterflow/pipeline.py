import json
from pathlib import Path

from .dedupe import merge
from .readers import read_source
from .validate import check_row


def load_sources(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {name.strip().lower(): (cfg["file"], int(cfg["priority"])) for name, cfg in raw.items()}


def ingest(data_dir):
    data_dir = Path(data_dir)
    sources = load_sources(data_dir / "sources.json")
    records, rejected, per_source = [], [], {}
    for name in sorted(sources):
        filename, priority = sources[name]
        rows = read_source(data_dir / filename, name)
        stats = {"rows": len(rows), "accepted": 0, "rejected": 0, "inactive": 0}
        for raw in rows:
            outcome, value = check_row(raw, priority)
            if outcome == "ok":
                records.append(value)
                stats["accepted"] += 1
            elif outcome == "inactive":
                stats["inactive"] += 1
            else:
                rejected.append({"source": name, "row": raw.row, "reason": value})
                stats["rejected"] += 1
        per_source[name] = stats
    roster, duplicates = merge(records)
    return per_source, rejected, roster, duplicates
