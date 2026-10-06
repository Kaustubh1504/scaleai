"""Assemble the fraud review report."""
from __future__ import annotations

from collections import Counter, defaultdict

from tripwire.duplicates import shared_answer_counts
from tripwire.loader import load_active_annotators, load_submissions
from tripwire.timing import rush_stats, task_medians

MIN_TIMED = 3
RUSH_LIMIT = 30.0
SHARED_LIMIT = 2


def flags_for(row: dict) -> list[str]:
    flags = []
    if row["timed"] >= MIN_TIMED and row["rush_rate"] >= RUSH_LIMIT:
        flags.append("rushing")
    if row["shared_answers"] >= SHARED_LIMIT:
        flags.append("copying")
    return flags


def worst_rusher(rush: dict[str, dict]) -> str | None:
    timed = {a: r for a, r in rush.items() if r["timed"] > 0}
    if not timed:
        return None
    return max(timed, key=lambda a: timed[a]["rush_rate"])


def build_report(data_dir=None) -> dict:
    active = load_active_annotators(data_dir / "annotators.csv" if data_dir else None)
    subs = load_submissions(active, data_dir / "submissions.csv" if data_dir else None)
    medians = task_medians(subs)
    rush = rush_stats(subs, medians)
    shared = shared_answer_counts(subs)

    rows = {}
    for annotator in active:
        r = rush.get(annotator, {"timed": 0, "rushed": 0, "rush_rate": 0.0})
        row = {
            "submissions": sum(1 for s in subs if s.annotator_id == annotator),
            "timed": r["timed"],
            "rushed": r["rushed"],
            "rush_rate": r["rush_rate"],
            "shared_answers": shared.get(annotator, 0),
        }
        row["flags"] = flags_for(row)
        rows[annotator] = row

    task_counts = Counter(s.task_id for s in subs)
    tasks = {t: {"submissions": task_counts[t], "median_s": medians.get(t)} for t in sorted(task_counts)}
    flagged = sorted(a for a, r in rows.items() if r["flags"])
    by_reason = defaultdict(int)
    for r in rows.values():
        for f in r["flags"]:
            by_reason[f] += 1
    return {
        "annotators": rows,
        "tasks": tasks,
        "summary": {
            "flagged": flagged,
            "flags_by_reason": dict(sorted(by_reason.items())),
            "worst_rusher": worst_rusher(rush),
        },
    }
