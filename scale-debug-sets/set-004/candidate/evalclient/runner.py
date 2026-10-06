import csv
from datetime import datetime
from pathlib import Path

from .client import ModelClient
from .config import load_config

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%b %d %Y")


def parse_due(value):
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"bad due date {value!r}")


def load_prompts(path):
    prompts = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            answer = row["answer"].strip()
            if not answer:
                continue
            prompts.append({
                "request_id": row["request_id"].strip().lower(),
                "question": row["question"].strip(),
                "answer": answer,
                "due": parse_due(row["due"]),
            })
    return sorted(prompts, key=lambda p: p["due"])


def collect_usage(client):
    items, cursor = [], None
    while True:
        page = client.usage_page(cursor)
        cursor = page.get("next_cursor")
        if not cursor:
            break
        items.extend(page["data"])
    return items


def run_batch(base_url, data_dir, api_key, sleep=None):
    data_dir = Path(data_dir)
    config = load_config(data_dir / "config.json")
    kwargs = {"sleep": sleep} if sleep else {}
    client = ModelClient(base_url, api_key, config, **kwargs)
    results = [client.grade(p["request_id"], p["question"], p["answer"]) for p in load_prompts(data_dir / "prompts.csv")]
    return results, collect_usage(client)
