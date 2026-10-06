from collections import defaultdict
from pathlib import Path

from .loader import load_episodes, load_frames, load_robots, load_tasks
from .validate import check_episode

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def task_table(verdicts):
    table = defaultdict(lambda: {"episodes": [], "total_s": 0.0})
    for v in verdicts:
        if v.valid:
            row = table[v.episode.task]
            row["episodes"].append(v.episode.id)
            row["total_s"] = round(row["total_s"] + v.duration_s, 2)
    return dict(sorted(table.items()))


def success_rates(verdicts):
    wins, totals = defaultdict(int), defaultdict(int)
    for v in verdicts:
        if v.valid:
            totals[v.episode.task] += 1
            wins[v.episode.task] += v.episode.outcome == "success"
    return {task: round(wins[task] / n, 3) for task, n in sorted(totals.items())}


def operator_table(verdicts):
    table = defaultdict(lambda: {"submitted": 0, "valid": 0, "valid_s": 0.0})
    for v in verdicts:
        row = table[v.episode.operator]
        row["submitted"] += 1
        if v.valid:
            row["valid"] += 1
            row["valid_s"] = round(row["valid_s"] + v.duration_s, 2)
    return dict(sorted(table.items()))


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    robots = load_robots(data_dir / "robots.json")
    tasks = load_tasks(data_dir / "tasks.csv")
    frames = load_frames(data_dir / "frames.jsonl")
    verdicts = [check_episode(ep, robots, tasks, frames) for ep in load_episodes(data_dir / "episodes.csv")]
    total_s = sum(v.duration_s for v in verdicts if v.valid)
    return {
        "episodes": {v.episode.id: {"valid": v.valid, "reason": v.reason, "duration_s": v.duration_s}
                     for v in verdicts},
        "tasks": task_table(verdicts),
        "summary": {
            "valid_episodes": sum(v.valid for v in verdicts),
            "valid_hours": round(total_s / 3600, 4),
            "success_rate": success_rates(verdicts),
            "operators": operator_table(verdicts),
        },
    }
