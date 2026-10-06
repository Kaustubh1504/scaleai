def task_metrics(episodes, stats):
    """Per-task numbers over valid episodes only."""
    grouped = {}
    for ep in episodes:
        if stats[ep.id].valid:
            grouped.setdefault(ep.task, []).append(ep)
    table = {}
    for task in sorted(grouped):
        eps = grouped[task]
        wins = sum(1 for ep in eps if ep.success)
        recorded_ms = sum(stats[ep.id].duration_ms for ep in eps)
        table[task] = {
            "episodes": len(eps),
            "success_rate": round(wins / len(eps), 3),
            "recorded_s": round(recorded_ms // 1000, 2),
        }
    return table
