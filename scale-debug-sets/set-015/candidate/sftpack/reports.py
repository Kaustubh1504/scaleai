from collections import Counter
from pathlib import Path

from .loader import load_config, load_conversations
from .render import render
from .turns import Rejected, check_order, count_tokens, merge_consecutive, normalise_roles, truncate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def split_tags(text):
    return [t.strip().lower() for t in text.split(",")]


def build_example(conv, config):
    messages = normalise_roles(conv["messages"], config["role_aliases"])
    messages = merge_consecutive(messages)
    check_order(messages)
    return truncate(messages, config["max_tokens"], config["per_message_overhead"])


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    conversations = load_conversations(data_dir / "conversations.json")
    examples, rejected = {}, {}
    for conv in conversations:
        try:
            messages, dropped = build_example(conv, config)
        except Rejected as exc:
            rejected[conv["id"]] = str(exc)
            continue
        examples[conv["id"]] = {
            "status": "truncated" if dropped else "ok",
            "tokens": count_tokens(messages, config["per_message_overhead"]),
            "turns": len(messages),
            "text": render(messages),
        }
    tags = Counter(tag for conv in conversations for tag in split_tags(conv["tags"]))
    longest = max(examples, key=lambda cid: (examples[cid]["tokens"], cid)) if examples else None
    return {
        "examples": examples,
        "rejected": rejected,
        "summary": {
            "sources": sorted({conv["source"] for conv in conversations}),
            "tag_counts": dict(sorted(tags.items())),
            "longest_example": longest,
        },
    }
