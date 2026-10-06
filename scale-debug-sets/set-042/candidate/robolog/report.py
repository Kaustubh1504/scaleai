from collections import Counter

from .loader import load_episodes, load_streams
from .metrics import task_metrics
from .validity import evaluate_all


def summarize(episodes, stats):
    valid = [ep for ep in episodes if stats[ep.id].valid]
    tags = Counter(tag for ep in valid for tag in ep.tags)
    operators = Counter(ep.operator for ep in episodes)
    rejected = Counter(s.reason for s in stats.values() if not s.valid)
    return {
        "valid_episodes": len(valid),
        "tag_counts": dict(sorted(tags.items())),
        "untagged": sorted(ep.id for ep in valid if not ep.tags),
        "operators": dict(sorted(operators.items())),
        "rejected": dict(sorted(rejected.items())),
    }


def build_report(episodes_path=None, streams_path=None):
    episodes = load_episodes(episodes_path)
    stats = evaluate_all(episodes, load_streams(streams_path))
    return {
        "episodes": {eid: s.as_dict() for eid, s in sorted(stats.items())},
        "tasks": task_metrics(episodes, stats),
        "summary": summarize(episodes, stats),
    }
