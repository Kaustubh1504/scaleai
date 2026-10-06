from collections import defaultdict
from pathlib import Path

from .config import load_thresholds
from .loader import load_episodes, load_robots
from .metrics import compute_metrics
from .validity import check_episode

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(rows):
    by_task = defaultdict(list)
    for row in rows:
        by_task[row["episode"].task].append(row)
    tasks = {}
    for task, items in sorted(by_task.items()):
        valid = [r for r in items if not r["reasons"]]
        wins = sum(1 for r in valid if r["episode"].success)
        tasks[task] = {
            "episodes": len(items),
            "valid": len(valid),
            "success_rate": round(wins / len(valid), 3) if valid else None,
        }
    valid_ms = sum(r["metrics"].span_ms for r in rows if not r["reasons"])
    return {"by_task": tasks, "valid_minutes": round(valid_ms / 60, 2)}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    thresholds = load_thresholds(data_dir / "config.json")
    robots = load_robots(data_dir / "robots.csv")
    rows = []
    for ep in load_episodes(data_dir / "episodes.csv", data_dir / "frames.json"):
        metrics = compute_metrics(ep, thresholds)
        reasons = check_episode(ep, metrics, robots.get(ep.robot_id), thresholds)
        rows.append({"episode": ep, "metrics": metrics, "reasons": reasons})
    return {
        "episodes": {
            r["episode"].episode_id: {
                "frames": r["metrics"].frames,
                "duration_s": r["metrics"].duration_s,
                "max_gap_ms": r["metrics"].max_gap_ms,
                "sync_rate": r["metrics"].sync_rate,
                "reasons": r["reasons"],
            }
            for r in sorted(rows, key=lambda r: r["episode"].episode_id)
        },
        "summary": summarize(rows),
    }
