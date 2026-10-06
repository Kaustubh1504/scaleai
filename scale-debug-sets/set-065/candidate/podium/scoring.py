"""Per-team scores: best submission per task, averaged over all tasks."""
from __future__ import annotations

from collections import defaultdict

TASKS = ("gsm8k", "humaneval", "mmlu")


def best_per_task(subs) -> dict[str, dict[str, float]]:
    best: dict[str, dict] = defaultdict(dict)
    for s in subs:
        current = best[s.team_id].get(s.task)
        if current is None or s.score > current.score:
            best[s.team_id][s.task] = s
    return {team: {task: float(s.score) for task, s in tasks.items()} for team, tasks in best.items()}


def tasks_attempted(subs) -> dict[str, int]:
    seen: dict[str, list] = defaultdict(list)
    for s in subs:
        seen[s.team_id].append(s.task)
    return {team: len(tasks) for team, tasks in seen.items()}


def overall(best: dict[str, float]) -> float:
    return round(sum(best.get(t, 0.0) for t in TASKS) / len(TASKS), 2)
