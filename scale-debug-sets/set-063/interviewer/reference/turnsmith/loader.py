"""Read the export config, conversation index and raw turn log."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def clean(value) -> str:
    return (value or "").strip()


def load_config(path: Path | None = None) -> dict:
    path = path or DATA_DIR / "config.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "system_prompt": raw["system_prompt"].strip(),
        "max_tokens": int(raw["max_tokens"]),
        "exclude_tags": {t.strip().lower() for t in raw.get("exclude_tags", [])},
    }


def parse_tags(raw: str) -> list[str]:
    return [t.strip().lower() for t in clean(raw).split(";") if t.strip()]


def load_conversations(path: Path | None = None) -> dict[str, list[str]]:
    """conv_id -> tags, in file order."""
    path = path or DATA_DIR / "conversations.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        return {clean(r["conv_id"]).lower(): parse_tags(r["tags"]) for r in csv.DictReader(fh)}


def load_turns(path: Path | None = None) -> dict[str, list[dict]]:
    """conv_id -> raw turns sorted by turn number."""
    path = path or DATA_DIR / "turns.csv"
    grouped = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            grouped[clean(r["conv_id"]).lower()].append(
                {"turn": int(clean(r["turn"])), "role": clean(r["role"]).lower(), "text": clean(r["text"])}
            )
    return {cid: sorted(turns, key=lambda t: t["turn"]) for cid, turns in grouped.items()}
