"""Build SFT examples and the export summary."""
from __future__ import annotations

from collections import Counter

from turnsmith.budget import count_tokens, fit_to_budget
from turnsmith.chat import to_messages
from turnsmith.loader import load_config, load_conversations, load_turns

DEFAULT_TAG = "general"


def build_dataset() -> dict:
    config = load_config()
    conversations = load_conversations()
    turns = load_turns()
    system = {"role": "system", "content": config["system_prompt"]}

    examples, rejected = {}, {}
    for cid, tags in conversations.items():
        tags = tags or [DEFAULT_TAG]
        if set(tags) & config["exclude_tags"]:
            rejected[cid] = "excluded"
            continue
        body = to_messages(turns.get(cid, []))
        if not body:
            rejected[cid] = "no_pair"
            continue
        fitted = fit_to_budget(system, body, config["max_tokens"])
        if fitted is None:
            rejected[cid] = "too_long"
            continue
        body, dropped = fitted
        messages = [system] + body
        examples[cid] = {
            "messages": messages,
            "tokens": count_tokens(messages),
            "dropped_messages": dropped,
            "tags": tags,
        }

    tag_counts = Counter(t for ex in examples.values() for t in ex["tags"])
    return {
        "examples": examples,
        "rejected": dict(sorted(rejected.items())),
        "summary": {
            "examples": len(examples),
            "rejected_by_reason": dict(sorted(Counter(rejected.values()).items())),
            "tag_counts": dict(sorted(tag_counts.items())),
            "total_tokens": sum(ex["tokens"] for ex in examples.values()),
        },
    }
