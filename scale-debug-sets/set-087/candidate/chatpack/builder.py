from collections import Counter
from pathlib import Path

from .budget import fit_budget
from .formatting import flatten, merge_consecutive, normalise_turns, render, split_pairs
from .loader import load_conversations, load_roles, load_sources

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(examples, rejected, tags_by_id):
    tags = Counter(tag for cid in examples for tag in tags_by_id[cid])
    per_source = Counter(ex["source"] for ex in examples.values())
    reasons = Counter(rejected.values())
    return {
        "tag_counts": dict(sorted(tags.items())),
        "examples_per_source": dict(sorted(per_source.items())),
        "rejected_by_reason": dict(sorted(reasons.items())),
    }


def build_dataset(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    aliases = load_roles(data_dir / "roles.csv")
    sources = load_sources(data_dir / "sources.csv")
    examples, rejected, tags_by_id = {}, {}, {}
    for conv in load_conversations(data_dir / "conversations.json"):
        cid = conv["id"]
        source = sources.get(conv["source"])
        if source is None:
            rejected[cid] = "unknown_source"
            continue
        if not source["include"]:
            continue
        turns = merge_consecutive(normalise_turns(conv["turns"], aliases))
        system, pairs = split_pairs(turns)
        if not pairs:
            rejected[cid] = "no_pair"
            continue
        kept, dropped, total = fit_budget(system, pairs, source["max_tokens"])
        if total > source["max_tokens"]:
            rejected[cid] = "too_long"
            continue
        examples[cid] = {
            "source": conv["source"],
            "roles": [turn.role for turn in flatten(system, kept)],
            "tokens": total,
            "dropped_pairs": dropped,
            "text": render(system, kept),
        }
        tags_by_id[cid] = conv["tags"]
    return {"examples": examples, "rejected": rejected, "summary": summarize(examples, rejected, tags_by_id)}
