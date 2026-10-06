"""Timing signals: per-task medians and rushed submissions."""
from __future__ import annotations

from collections import defaultdict

RUSH_FRACTION = 0.25


# VERIFIED
def median(values: list[int]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def task_medians(subs) -> dict[str, float]:
    durations = defaultdict(list)
    for s in subs:
        if s.duration_s is not None:
            durations[s.task_id].append(s.duration_s)
    return {task: median(vals) for task, vals in durations.items()}


def is_rushed(sub, medians: dict[str, float]) -> bool:
    return sub.duration_s < RUSH_FRACTION * medians[sub.task_id]


def rush_stats(subs, medians: dict[str, float]) -> dict[str, dict]:
    """annotator -> {timed, rushed, rush_rate} (rate is a percentage)."""
    stats: dict[str, dict] = defaultdict(lambda: {"timed": 0, "rushed": 0})
    for s in subs:
        if s.duration_s is None:
            continue
        row = stats[s.annotator_id]
        row["timed"] += 1
        if is_rushed(s, medians):
            row["rushed"] += 1
    for row in stats.values():
        row["rush_rate"] = round(100 * row["rushed"] / row["timed"], 1)
    return dict(stats)
