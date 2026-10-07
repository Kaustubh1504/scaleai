from pathlib import Path

from .loader import load_config, load_conversations, validate, with_system
from .masks import assistant_spans
from .render import render, total_tokens, truncate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_examples(conversations, config):
    examples, rejected = {}, {}
    for conv in conversations:
        reason = validate(conv.messages)
        if reason:
            rejected[conv.conv_id] = reason
            continue
        messages = with_system(conv.messages, config["default_system"])
        kept = truncate(messages, config["max_tokens"])
        if kept is None:
            rejected[conv.conv_id] = "too_long"
            continue
        examples[conv.conv_id] = {
            "messages": kept,
            "text": render(kept),
            "tokens": total_tokens(kept),
            "spans": assistant_spans(kept),
            "turns_dropped": len(messages) - len(kept),
        }
    return examples, rejected


def summarize(examples, rejected):
    tokens = [ex["tokens"] for ex in examples.values()]
    return {
        "examples": len(examples),
        "rejected": dict(sorted(rejected.items())),
        "assistant_turns": sum(1 for ex in examples.values() for m in ex["messages"] if m.role == "assistant"),
        "mean_tokens": round(sum(tokens) / len(tokens), 1) if tokens else None,
    }


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    config = load_config(data_dir / "config.json")
    examples, rejected = build_examples(load_conversations(data_dir / "conversations.jsonl"), config)
    return {
        "examples": {cid: {k: v for k, v in ex.items() if k != "messages"} for cid, ex in examples.items()},
        "summary": summarize(examples, rejected),
    }
