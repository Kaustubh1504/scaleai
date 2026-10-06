"""Shared-answer signal: identical answers from different annotators on one task."""
from __future__ import annotations

import re
from collections import Counter, defaultdict


def answer_key(text: str) -> str:
    """Lower-case, collapse whitespace, drop trailing . and !"""
    collapsed = re.sub(r"\s+", " ", text.strip().lower())
    return collapsed.rstrip(".!").strip()


def has_twin(sub, same_task) -> bool:
    key = answer_key(sub.answer)
    if not key:
        return False
    for other in same_task:
        if other.annotator_id == sub.annotator_id:
            continue
        if answer_key(other.answer) == key:
            return True
    return False


def shared_answer_counts(subs) -> Counter:
    by_task = defaultdict(list)
    for s in subs:
        by_task[s.task_id].append(s)
    counts: Counter = Counter()
    for s in subs:
        if has_twin(s, by_task[s.task_id]):
            counts[s.annotator_id] += 1
    return counts
