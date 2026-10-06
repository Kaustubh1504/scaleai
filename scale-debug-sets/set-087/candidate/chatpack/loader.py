import csv
import json

DEFAULT_MAX_TOKENS = 64
TRUTHY = {"yes", "y", "true", "1"}


def clean(value):
    return str(value if value is not None else "").strip()


def norm_key(value):
    return clean(value).lower()


def parse_tags(raw):
    return [p.strip().lower() for p in clean(raw).split(";")]


def load_roles(path):
    """alias -> canonical role name."""
    aliases = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            alias = norm_key(row["alias"])
            if alias:
                aliases[alias] = norm_key(row["role"])
    return aliases


def load_sources(path):
    sources = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = norm_key(row["source"])
            limit = clean(row["max_tokens"])
            sources[name] = {
                "max_tokens": int(limit) if limit else DEFAULT_MAX_TOKENS,
                "include": norm_key(row["include"]) in TRUTHY,
            }
    return sources


def load_conversations(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    conversations = []
    for item in raw:
        conversations.append({
            "id": norm_key(item["id"]),
            "source": norm_key(item.get("source")),
            "tags": parse_tags(item.get("tags")),
            "turns": item.get("turns") or [],
        })
    return conversations
